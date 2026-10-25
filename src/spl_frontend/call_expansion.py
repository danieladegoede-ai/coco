"""Shared structural expansion for code-mine children and executable calls."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from spl_frontend.codegen import CodeGenerator, CodegenContext, SymbolEnvironment
from spl_frontend.codegen_ir import (
    Assign, CodegenError, IRFragment, StorageKind, StorageLocation,
    clone_fragment, combine_fragments,
)
from spl_frontend.semantic_model import SemanticType
from spl_frontend.tree import NodeKind
from spl_frontend.tree_walkers import iter_list_items

if TYPE_CHECKING:
    from spl_frontend.function_templates import FunctionTemplate


CallTask = IRFragment | tuple[int, StorageLocation]


class TemplateCallEmitter:
    """Clone immutable templates; capture every actual before formal copies.

    A template builder supplies its live read-only catalogue while preparing
    children before parents. The executable inliner supplies the completed
    immutable catalogue. Both use exactly the same expansion semantics.
    """

    def __init__(self, generator: CodeGenerator,
                 templates: Mapping[int, FunctionTemplate], *, max_instructions: int) -> None:
        if type(max_instructions) is not int or max_instructions < 1:
            raise CodegenError("GEN-EXPANSION-LIMIT", "Instruction budget must be a positive integer.")
        self.generator = generator
        self.context = generator.context
        self.checked = generator.checked
        self.resolved = self.checked.resolved
        self.tree = self.resolved.tree
        self.templates = templates
        self.max_instructions = max_instructions

    def fail(self, code: str, message: str, node_id: int | None = None) -> None:
        raise CodegenError(code, message, node_id=node_id,
                           span=self.resolved.source_location_by_node.get(node_id))

    def _check_budget(self, fragment: IRFragment, node_id: int | None) -> None:
        if len(fragment.instructions) > self.max_instructions:
            self.fail("GEN-EXPANSION-LIMIT", "Static inline expansion exceeds the instruction resource limit.", node_id)

    def plan_call(self, call_node_id: int, destination: StorageLocation | None,
                  environment: SymbolEnvironment, context: CodegenContext) -> list[CallTask]:
        """Return ordered TERM jobs and fragments for the backend work stack.

        Planning a nested actual never recursively invokes generation. Every
        actual is captured before any formal is populated at runtime.
        """
        if context is not self.context:
            self.fail("GEN-CONTEXT", "Call uses a different compilation context.", call_node_id)
        call = self.tree.get_node(call_node_id)
        if call.kind is not NodeKind.INNER or call.contents != "CALL" or len(call.child_ids) != 4:
            self.fail("GEN-CALL-SHAPE", "Expected CALL -> NAME ( INPUT ).", call_node_id)
        name, left, inputs, right = (self.tree.get_node(i) for i in call.child_ids)
        if (left.contents, inputs.contents, right.contents) != ("(", "INPUT", ")"):
            self.fail("GEN-CALL-SHAPE", "Malformed CALL production.", call_node_id)
        symbol_id = self.resolved.binding_by_name_node.get(name.node_id)
        template = self.templates.get(symbol_id)
        if template is None:
            self.fail("GEN-CALL-TEMPLATE", "No prepared function template.", call_node_id)
        symbol = self.resolved.symbols[symbol_id]
        if symbol.scope_id != self.resolved.scope_by_node[call_node_id]:
            self.fail("GEN-CALL-SCOPE", "Call must target a direct lexical child.", call_node_id)
        numeric = template.return_type is SemanticType.NUMERIC
        if numeric != (destination is not None):
            self.fail("GEN-CALL-CONTEXT", "Call continuation disagrees with return kind.", call_node_id)
        actuals = tuple(iter_list_items(self.tree, inputs.node_id))
        expected = len(template.formal_symbol_ids)
        if len(actuals) != expected:
            noun = "argument" if expected == 1 else "arguments"
            self.fail("GEN-ARITY", f"Function expects {expected} {noun}; got {len(actuals)}.", call_node_id)
        capture_slots = tuple(self.context.new_storage(StorageKind.CAPTURE) for _ in actuals)
        storage_map = {slot: self.context.allocator.new_storage(slot.kind, slot.value_type)
                       for slot in template.declarations}
        cloned = clone_fragment(IRFragment(template.declarations, template.instructions),
                                context.allocator, symbol_remap=environment, storage_remap=storage_map)
        copies = tuple(Assign(storage_map[template.storage_by_symbol[formal]], actual)
                       for formal, actual in zip(template.formal_symbol_ids, capture_slots))
        tail = () if destination is None else (Assign(destination, storage_map[template.return_storage]),)
        expansion = combine_fragments(IRFragment(capture_slots), IRFragment(instructions=copies),
                                      cloned, IRFragment(instructions=tail))
        self._check_budget(expansion, call_node_id)
        # Copies and cloned body execute after *all* complete TERM evaluations.
        return [IRFragment(declarations=capture_slots),
                *((term.node_id, slot) for term, slot in zip(actuals, capture_slots)),
                expansion]

    def emit_call(self, call_node_id: int, destination: StorageLocation | None,
                  environment: SymbolEnvironment, context: CodegenContext) -> IRFragment:
        fragments = []
        for task in self.plan_call(call_node_id, destination, environment, context):
            if isinstance(task, IRFragment):
                fragments.append(task)
            else:
                term_id, slot = task
                fragments.append(self.generator.emit_term(term_id, slot, environment))
        fragment = combine_fragments(*fragments)
        self._check_budget(fragment, call_node_id)
        return fragment
