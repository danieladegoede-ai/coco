"""Immutable reusable code-mine records, indexed by resolved function identity."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from types import MappingProxyType

from spl_frontend.codegen import CodeGenerator, CodegenContext
from spl_frontend.call_expansion import TemplateCallEmitter
from spl_frontend.codegen_ir import (
    CodeMineSection, IRFragment, Instruction, Label,
    LabelRef, StorageKind, StorageLocation, StorageRef, SymbolRef,
    combine_fragments,
)
from spl_frontend.expansion_environment import ExpansionEnvironment
from spl_frontend.name_analysis import NameAnalysisError, build_call_hierarchy
from spl_frontend.semantic_model import CheckedProgram, SemanticType, SymbolKind
from spl_frontend.target_writer import TargetWriter
from spl_frontend.tree import NodeKind
from spl_frontend.tree_walkers import function_parts, iter_list_items, iter_preorder, program_parts

@dataclass(frozen=True, slots=True)
class FunctionTemplate:
    symbol_id: int
    body_scope_id: int
    body_p_node_id: int
    formal_symbol_ids: tuple[int, ...]
    local_symbol_ids: tuple[int, ...]
    child_function_ids: tuple[int, ...]
    captured_symbol_ids: tuple[int, ...]
    return_type: SemanticType
    return_term_node_id: int | None
    storage_by_symbol: Mapping[int, StorageLocation]
    declarations: tuple[StorageRef, ...]
    instructions: tuple[Instruction, ...]
    labels: tuple[LabelRef, ...]
    return_storage: StorageRef | None = None
    capture_storage_by_symbol: Mapping[int, StorageLocation] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("formal_symbol_ids", "local_symbol_ids", "child_function_ids",
                     "captured_symbol_ids", "declarations", "instructions", "labels"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        for name in ("storage_by_symbol", "capture_storage_by_symbol"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        if self.return_type not in {SemanticType.PROCEDURE, SemanticType.NUMERIC}:
            raise ValueError("Function template requires a checked return type.")
        numeric = self.return_type is SemanticType.NUMERIC
        if numeric and (self.return_term_node_id is None or self.return_storage is None):
            raise ValueError("Numeric templates require a return TERM and storage.")
        if not numeric and (self.return_term_node_id is not None or self.return_storage is not None):
            raise ValueError("Procedure templates cannot have numeric return metadata.")
        identities = (self.symbol_id, self.body_scope_id, self.body_p_node_id,
                      *self.formal_symbol_ids, *self.local_symbol_ids,
                      *self.child_function_ids, *self.captured_symbol_ids)
        if any(type(i) is not int or i < 1 for i in identities):
            raise ValueError("Template identities must be positive integers.")
        if len(set(self.formal_symbol_ids + self.local_symbol_ids)) != len(self.formal_symbol_ids + self.local_symbol_ids):
            raise ValueError("Template formals and locals must be distinct.")
        IRFragment(self.declarations, self.instructions)
        defined_labels = tuple(i.label for i in self.instructions if isinstance(i, Label))
        if self.labels != defined_labels or len(set(self.labels)) != len(self.labels):
            raise ValueError("Template labels must match unique instruction definitions.")
        referenced_labels = {getattr(i, f.name) for i in self.instructions for f in fields(i)
                             if isinstance(getattr(i, f.name), LabelRef)}
        if not referenced_labels.issubset(self.labels):
            raise ValueError("Template has an undefined label.")
        if set(self.storage_by_symbol) != set(self.formal_symbol_ids + self.local_symbol_ids):
            raise ValueError("Template bindings must cover exactly its parameters and locals.")
        if set(self.capture_storage_by_symbol) != set(self.captured_symbol_ids):
            raise ValueError("Template capture bindings disagree with capture IDs.")
        if len(set(self.declarations)) != len(self.declarations):
            raise ValueError("Template declarations must be unique.")
        if not set(self.storage_by_symbol.values()).issubset(self.declarations):
            raise ValueError("Template bindings require owned declarations.")
        if set(self.capture_storage_by_symbol.values()) & set(self.declarations):
            raise ValueError("Captured storage cannot be owned by the template.")
        if self.return_storage is not None and self.return_storage not in self.declarations:
            raise ValueError("Return storage must be owned by the template.")


MAX_EXPANDED_INSTRUCTIONS = 1_000_000


class _TemplateBuilder(TemplateCallEmitter):
    """Per-compilation immutable templates, sharing the backend's allocator."""

    def __init__(self, generator: CodeGenerator) -> None:
        self._templates: dict[int, FunctionTemplate] = {}
        super().__init__(generator, MappingProxyType(self._templates),
                         max_instructions=MAX_EXPANDED_INSTRUCTIONS)
        self.preparation_order: list[int] = []
        generator.call_emitter = self
        try:
            build_call_hierarchy(self.resolved)
        except NameAnalysisError as exc:
            self.fail("GEN-TEMPLATE-HIERARCHY", str(exc), exc.node_id)
        self._prepare_templates()

    def _prepare_templates(self) -> None:
        functions = [s for s in self.resolved.symbols.values() if s.kind is SymbolKind.FUNCTION]
        functions.sort(key=lambda s: -self.resolved.scopes[s.body_scope_id].depth)
        for symbol in functions:
            declaration = self.tree.get_node(symbol.declaration_node_id)
            if declaration.parent_id is None:
                self.fail("GEN-TEMPLATE-SHAPE", "Function NAME has no F_TYPE parent.", declaration.node_id)
            parts = function_parts(self.tree, declaration.parent_id)
            body = program_parts(self.tree, parts.body.node_id)
            scope_id = symbol.body_scope_id
            if scope_id is None or self.resolved.scopes[scope_id].p_node_id != parts.body.node_id:
                self.fail("GEN-TEMPLATE-SCOPE", "Function body scope disagrees with its P.", declaration.node_id)
            locals_ = tuple(self.resolved.binding_by_name_node[n.node_id]
                            for n in iter_list_items(self.tree, body.variables.node_id))
            children = tuple(self.resolved.binding_by_name_node[function_parts(self.tree, n.node_id).name.node_id]
                             for n in iter_list_items(self.tree, body.functions.node_id))
            if any(child not in self._templates for child in children):
                self.fail("GEN-TEMPLATE-ORDER", "Child template must precede parent.", declaration.node_id)
            ancestors = set()
            parent = self.resolved.scopes[scope_id].parent_id
            while parent is not None:
                if parent in ancestors:
                    self.fail("GEN-TEMPLATE-CYCLE", "Cyclic lexical scope chain.", declaration.node_id)
                ancestors.add(parent)
                parent = self.resolved.scopes[parent].parent_id
            captured = {}
            subtrees = [parts.body.node_id]
            if parts.return_term is not None:
                subtrees.append(parts.return_term.node_id)
            for subtree in subtrees:
                for node in iter_preorder(self.tree, subtree):
                    identity = self.resolved.binding_by_name_node.get(node.node_id)
                    if identity is not None:
                        used = self.resolved.symbols[identity]
                        if used.kind is not SymbolKind.FUNCTION and used.scope_id in ancestors:
                            captured[identity] = SymbolRef(identity)
            owned = {identity: self.context.new_storage(StorageKind.EXPANSION)
                     for identity in symbol.parameter_ids + locals_}
            environment = ExpansionEnvironment(scope_id, {**owned, **captured})
            fragment = combine_fragments(
                IRFragment(declarations=tuple(owned.values())),
                self.generator.emit_algorithm(body.algorithm.node_id, environment),
            )
            return_storage = None
            if parts.return_term is not None:
                return_storage = self.context.new_storage(StorageKind.RETURN)
                fragment = combine_fragments(fragment, IRFragment(declarations=(return_storage,)),
                    self.generator.emit_term(parts.return_term.node_id, return_storage, environment))
            self._check_budget(fragment, declaration.node_id)
            self._templates[symbol.symbol_id] = FunctionTemplate(
                symbol.symbol_id, scope_id, parts.body.node_id, symbol.parameter_ids,
                locals_, children, tuple(captured), symbol.value_type,
                parts.return_term.node_id if parts.return_term is not None else None,
                owned, fragment.declarations, fragment.instructions,
                tuple(i.label for i in fragment.instructions if isinstance(i, Label)),
                return_storage, captured,
            )
            self.preparation_order.append(symbol.symbol_id)

    def code_mine(self) -> tuple[CodeMineSection, ...]:
        # Reuse the target serializer. This view is never a closed executable;
        # free SymbolRefs are legal here and everything is line-commented later.
        class SymbolView:
            symbols = self.resolved.symbols
            numeric_mode = self.checked.numeric_mode
        view = SymbolView()
        writer = TargetWriter()
        sections = []
        for identity in self.preparation_order:
            t = self._templates[identity]
            symbol = self.resolved.symbols[identity]
            lines = [f"symbol {identity}; {symbol.value_type.value}; scope {t.body_scope_id}",
                     "parameters: " + ", ".join(f"{i} -> {self.context.allocator.storage_name(t.storage_by_symbol[i])}" for i in t.formal_symbol_ids),
                     "captures: " + ", ".join(str(i) for i in t.captured_symbol_ids)]
            lines.extend(f"{slot.value_type.value} {self.context.allocator.storage_name(slot)};" for slot in t.declarations)
            for instruction in t.instructions:
                lines.extend(writer._render_instruction(instruction, view))
            if t.return_storage is not None:
                lines.append("return value: " + self.context.allocator.storage_name(t.return_storage))
            sections.append(CodeMineSection(symbol.internal_name, "\n".join(lines)))
        return tuple(sections)


@dataclass(frozen=True, slots=True)
class PreparedFunctionTemplates:
    """Immutable handoff for the later inliner; no executable main is emitted."""

    checked: CheckedProgram
    templates: Mapping[int, FunctionTemplate]
    preparation_order: tuple[int, ...]
    code_mine: tuple[CodeMineSection, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "templates", MappingProxyType(dict(self.templates)))
        object.__setattr__(self, "preparation_order", tuple(self.preparation_order))
        object.__setattr__(self, "code_mine", tuple(self.code_mine))


def prepare_function_templates(
    checked: CheckedProgram, *, context: CodegenContext | None = None,
) -> PreparedFunctionTemplates:
    """Prepare every function child-before-parent, including uncalled bodies.

    Child calls expand only inside these inactive templates. The later #30
    inliner owns expansion into executable main and caller continuations.
    Supplying its shared context keeps all storage/label allocation disjoint.
    """
    builder = _TemplateBuilder(CodeGenerator(checked, context=context))
    return PreparedFunctionTemplates(checked, builder.templates,
                                     tuple(builder.preparation_order), builder.code_mine())
