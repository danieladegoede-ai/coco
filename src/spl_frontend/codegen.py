"""Algorithm and arithmetic lowering from a CheckedProgram to structured IR.

This module never reparses names or accepts unvalidated syntax. It consumes the
resolved symbol IDs and selected whole-program NumericMode, and its only call
handling is an explicit extension hook for the separately owned inliner.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from spl_frontend.boolean_codegen import BooleanCodeGenerator
from spl_frontend.codegen_ir import (
    Assign,
    BinaryAssign,
    BinaryOperator,
    CodegenError,
    CompareOperator,
    Comment,
    ConditionalJump,
    FreshNameAllocator,
    IRFragment,
    Jump,
    Label,
    LabelRef,
    Nop,
    NumberLiteral,
    Operand,
    PrintNumber,
    PrintString,
    StorageKind,
    StorageLocation,
    StorageRef,
    StringLiteral,
    SymbolRef,
    TargetProgram,
    TargetScalarType,
    UnaryAssign,
    UnaryOperator,
    combine_fragments,
)
from spl_frontend.semantic_model import CheckedProgram, NumericMode, SemanticType, SymbolKind
from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode
from spl_frontend.tree_walkers import iter_list_items, program_parts


SymbolEnvironment = Mapping[int, StorageLocation]


@dataclass(slots=True)
class CodegenContext:
    """Per-compilation shared allocator and checked semantic snapshot."""

    checked: CheckedProgram
    allocator: FreshNameAllocator = field(default_factory=FreshNameAllocator)

    def __post_init__(self) -> None:
        if not isinstance(self.checked, CheckedProgram):
            raise CodegenError("CODEGEN-CHECKED-PROGRAM", "Code generation requires a CheckedProgram.")
        if not isinstance(self.allocator, FreshNameAllocator):
            raise CodegenError("CODEGEN-ALLOCATOR", "CodegenContext needs a FreshNameAllocator.")

    @property
    def numeric_mode(self) -> NumericMode:
        return self.checked.numeric_mode

    @property
    def target_scalar_type(self) -> TargetScalarType:
        return TargetScalarType.from_mode(self.numeric_mode)

    def new_temp(self) -> StorageRef:
        return self.allocator.new_temporary(self.target_scalar_type)

    def new_storage(self, kind: StorageKind) -> StorageRef:
        return self.allocator.new_storage(kind, self.target_scalar_type)

    def new_label(self) -> LabelRef:
        return self.allocator.new_label()

    def resolve_symbol(self, symbol_id: int, environment: SymbolEnvironment | None = None) -> StorageLocation:
        symbol = self.checked.resolved.symbols.get(symbol_id)
        if symbol is None:
            raise CodegenError("CODEGEN-UNKNOWN-SYMBOL", f"Resolved symbol {symbol_id} does not exist.")
        if symbol.kind not in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}:
            raise CodegenError("CODEGEN-NON-VARIABLE", f"Function symbol {symbol_id} used as a value.")
        if environment is not None and symbol_id in environment:
            replacement = environment[symbol_id]
            if not isinstance(replacement, (SymbolRef, StorageRef)):
                raise CodegenError("CODEGEN-ENVIRONMENT", f"Symbol {symbol_id} maps to invalid storage.")
            if isinstance(replacement, StorageRef) and replacement.value_type is not self.target_scalar_type:
                raise CodegenError("CODEGEN-ENVIRONMENT-TYPE", "Expansion storage has the wrong numeric type.")
            if isinstance(replacement, SymbolRef):
                mapped = self.checked.resolved.symbols.get(replacement.symbol_id)
                if mapped is None or mapped.kind not in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}:
                    raise CodegenError("CODEGEN-ENVIRONMENT", "Symbol remap points to invalid variable storage.")
            return replacement
        return SymbolRef(symbol_id)


class CallEmitter(Protocol):
    """Extension point for the separate inliner; not an alternate call runtime."""

    def emit_call(
        self,
        call_node_id: int,
        destination: StorageLocation | None,
        environment: SymbolEnvironment,
        context: CodegenContext,
    ) -> IRFragment: ...


class CodeGenerator:
    """Emit target instructions for simple forms and explicit control flow.

    ``environment`` maps resolved declaration IDs to this expansion's storage.
    With no mapping, top-level symbols use their stable semantic internal names.
    Function calls require the provided ``CallEmitter`` hook; no call is silently
    left as a target-language call or lowered by textual identifier substitution.
    """

    def __init__(
        self,
        checked: CheckedProgram,
        *,
        context: CodegenContext | None = None,
        call_emitter: CallEmitter | None = None,
    ) -> None:
        self.context = context if context is not None else CodegenContext(checked)
        if self.context.checked is not checked and self.context.checked != checked:
            raise CodegenError("CODEGEN-CONTEXT", "Shared context belongs to a different CheckedProgram.")
        self.checked = checked
        self.tree = checked.resolved.tree
        self.call_emitter = call_emitter

    def emit_term(
        self,
        term_node_id: int,
        destination: StorageLocation,
        environment: SymbolEnvironment | None = None,
    ) -> IRFragment:
        # A work stack keeps parser-accepted terms and imported deep trees from
        # consuming an additional Python frame at each target operation.
        tasks = [(term_node_id, destination)]
        fragments = []
        while tasks:
            task = tasks.pop()
            if isinstance(task, IRFragment):
                fragments.append(task)
                continue
            node_id, result = task
            term = self._require_node(node_id, NodeKind.INNER, "TERM")
            self._require_checked_type(term, SemanticType.NUMERIC)
            children = self._children(term)
            if len(children) == 1:
                leaf = children[0]
                if leaf.kind is NodeKind.INNER and leaf.contents == "CALL":
                    fragments.append(self._emit_call(leaf.node_id, result, environment))
                    continue
                if leaf.kind is NodeKind.LEAF:
                    if leaf.contents.startswith("#"):
                        symbol_id = self.checked.resolved.binding_by_name_node.get(leaf.node_id)
                        if symbol_id is None:
                            raise CodegenError("CODEGEN-UNBOUND-NAME", "Name lacks a resolved binding.", node_id=leaf.node_id)
                        value = self.context.resolve_symbol(symbol_id, environment)
                    else:
                        value = NumberLiteral(leaf.contents)
                    if value != result:
                        fragments.append(IRFragment(instructions=(Assign(result, value),)))
                    continue
            if not children or children[0].kind is not NodeKind.LEAF:
                raise CodegenError("CODEGEN-TERM-SHAPE", "TERM has an invalid production shape.", node_id=node_id)
            operator = children[0].contents
            if operator == "neg" and len(children) == 4 and children[2].contents == "TERM":
                value = self.context.new_temp()
                fragments.append(IRFragment(declarations=(value,)))
                tasks.extend((IRFragment(instructions=(UnaryAssign(result, UnaryOperator.NEGATE, value),)),
                              (children[2].node_id, value)))
            elif operator in {"add", "sub", "mul", "div", "mod"} and len(children) == 5 and all(c.contents == "TERM" for c in children[2:4]):
                left, right = self.context.new_temp(), self.context.new_temp()
                fragments.append(IRFragment(declarations=(left, right)))
                tasks.extend((IRFragment(instructions=(BinaryAssign(result, BinaryOperator.from_spl(operator), left, right),)),
                              (children[3].node_id, right), (children[2].node_id, left)))
            else:
                raise CodegenError("CODEGEN-TERM-SHAPE", "Unsupported TERM production.", node_id=node_id)
        return combine_fragments(*fragments)

    def emit_instr(
        self,
        instruction_node_id: int,
        environment: SymbolEnvironment | None = None,
    ) -> IRFragment:
        node = self._require_node(instruction_node_id, NodeKind.INNER, "INSTR")
        children = self._children(node)
        if not children:
            raise CodegenError("CODEGEN-INSTR-SHAPE", "INSTR has no production children.", node_id=node.node_id)
        first = children[0]

        if first.kind is NodeKind.LEAF:
            if first.contents == "print":
                if len(children) != 2 or children[1].contents != "OUTP":
                    raise CodegenError("CODEGEN-PRINT-SHAPE", "print INSTR has an invalid OUTP.", node_id=node.node_id)
                outp = self._children(children[1])
                if outp and outp[0].kind is NodeKind.LEAF and outp[0].contents.startswith('"'):
                    token = outp[0].contents
                    if len(token) < 2 or not token.endswith('"'):
                        raise CodegenError("CODEGEN-STRING", "Malformed STRING terminal.", node_id=outp[0].node_id)
                    return IRFragment(instructions=(PrintString(StringLiteral(token[1:-1])),))
                if len(outp) != 3 or outp[1].contents != "TERM":
                    raise CodegenError("CODEGEN-PRINT-SHAPE", "Numeric OUTP must contain one TERM.", node_id=node.node_id)
                temp = self.context.new_temp()
                value = self.emit_term(outp[1].node_id, temp, environment)
                return combine_fragments(
                    IRFragment(declarations=(temp,)), value, IRFragment(instructions=(PrintNumber(temp),))
                )
            if first.contents == "nop":
                return IRFragment(instructions=(Nop(),))
            if first.contents == "comment":
                if len(children) != 2 or children[1].kind is not NodeKind.LEAF or not children[1].contents.startswith('"'):
                    raise CodegenError("CODEGEN-COMMENT-SHAPE", "comment INSTR must contain a STRING.", node_id=node.node_id)
                token = children[1].contents
                if len(token) < 2 or not token.endswith('"'):
                    raise CodegenError("CODEGEN-STRING", "Malformed comment STRING terminal.", node_id=children[1].node_id)
                return IRFragment(instructions=(Comment(token[1:-1]),))
            raise CodegenError(
                "CODEGEN-INSTR-KEYWORD", f"Unsupported simple instruction {first.contents!r}.", node_id=node.node_id
            )

        if first.kind is NodeKind.INNER:
            if first.contents == "ASSIGN":
                assign_children = self._children(first)
                if len(assign_children) != 3 or assign_children[1].contents != "=":
                    raise CodegenError("CODEGEN-ASSIGN-SHAPE", "ASSIGN has an invalid production shape.", node_id=first.node_id)
                target_leaf = assign_children[0]
                symbol_id = self.checked.resolved.binding_by_name_node.get(target_leaf.node_id)
                if symbol_id is None:
                    raise CodegenError("CODEGEN-UNBOUND-NAME", "Assignment target lacks a symbol binding.", node_id=target_leaf.node_id)
                target = self.context.resolve_symbol(symbol_id, environment)
                return self.emit_term(assign_children[2].node_id, target, environment)
            if first.contents == "CALL":
                return self._emit_call(first.node_id, None, environment)
            if first.contents == "BRANCH":
                return self._emit_branch(first.node_id, environment)
            if first.contents == "LOOP":
                return self._emit_loop(first.node_id, environment)

        raise CodegenError(
            "CODEGEN-INSTR-NODE", f"Unsupported INSTR production {first.contents!r}.", node_id=node.node_id
        )

    def emit_bool(
        self,
        bool_node_id: int,
        true_label: LabelRef,
        false_label: LabelRef,
        environment: SymbolEnvironment | None = None,
    ) -> IRFragment:
        """Delegate Boolean logic to the separately testable lowering pass."""
        return BooleanCodeGenerator(self.context, self.emit_term).emit_bool(
            bool_node_id, true_label, false_label, environment
        )

    def emit_algorithm(
        self,
        algorithm_node_id: int,
        environment: SymbolEnvironment | None = None,
    ) -> IRFragment:
        return self._emit_control("algo", algorithm_node_id, environment)

    def _emit_branch(self, branch_node_id: int, environment: SymbolEnvironment | None) -> IRFragment:
        return self._emit_control("branch", branch_node_id, environment)

    def _emit_loop(self, loop_node_id: int, environment: SymbolEnvironment | None) -> IRFragment:
        return self._emit_control("loop", loop_node_id, environment)

    def _emit_control(self, kind: str, node_id: int, environment: SymbolEnvironment | None) -> IRFragment:
        tasks = [(kind, node_id)]
        fragments = []
        while tasks:
            task = tasks.pop()
            if isinstance(task, IRFragment):
                fragments.append(task)
                continue
            kind, node_id = task
            if kind == "algo":
                self._require_node(node_id, NodeKind.INNER, "ALGO")
                tasks.extend(("instr", item.node_id) for item in reversed(list(iter_list_items(self.tree, node_id))))
            elif kind == "instr":
                node = self._require_node(node_id, NodeKind.INNER, "INSTR")
                children = self._children(node)
                if children and children[0].kind is NodeKind.INNER and children[0].contents in {"BRANCH", "LOOP"}:
                    tasks.append((children[0].contents.lower(), children[0].node_id))
                else:
                    fragments.append(self.emit_instr(node_id, environment))
            elif kind == "branch":
                node = self._require_node(node_id, NodeKind.INNER, "BRANCH")
                c = self._children(node)
                if len(c) != 10 or c[1].contents != "BOOL" or c[4].contents != "ALGO" or c[8].contents != "ALGO":
                    raise CodegenError("CODEGEN-BRANCH-SHAPE", "Invalid BRANCH production.", node_id=node_id)
                yes, no, end = self.context.new_label(), self.context.new_label(), self.context.new_label()
                fragments.append(self.emit_bool(c[1].node_id, yes, no, environment))
                tasks.extend(reversed([
                    IRFragment(instructions=(Label(yes),)), ("algo", c[4].node_id),
                    IRFragment(instructions=(Jump(end), Label(no))), ("algo", c[8].node_id),
                    IRFragment(instructions=(Label(end),)),
                ]))
            elif kind == "loop":
                node = self._require_node(node_id, NodeKind.INNER, "LOOP")
                c = self._children(node)
                if len(c) != 6:
                    raise CodegenError("CODEGEN-LOOP-SHAPE", "Invalid LOOP production.", node_id=node_id)
                pre = c[0].kind is NodeKind.INNER and c[0].contents == "COND"
                if pre and (c[1].contents != "BOOL" or c[4].contents != "ALGO"):
                    raise CodegenError("CODEGEN-LOOP-SHAPE", "Invalid pre-test LOOP.", node_id=node_id)
                if not pre and (c[0].contents != "do" or c[2].contents != "ALGO" or c[4].contents != "COND" or c[5].contents != "BOOL"):
                    raise CodegenError("CODEGEN-LOOP-SHAPE", "Invalid post-test LOOP.", node_id=node_id)
                until = self._is_until_condition(c[0 if pre else 4].node_id)
                start, body, end = self.context.new_label(), self.context.new_label(), self.context.new_label()
                if pre:
                    condition = self.emit_bool(c[1].node_id, end if until else body, body if until else end, environment)
                    tasks.extend(reversed([
                        IRFragment(instructions=(Label(start),)), condition,
                        IRFragment(instructions=(Label(body),)), ("algo", c[4].node_id),
                        IRFragment(instructions=(Jump(start), Label(end))),
                    ]))
                else:
                    condition = self.emit_bool(c[5].node_id, end if until else start, start if until else end, environment)
                    tasks.extend(reversed([
                        IRFragment(instructions=(Label(start),)), ("algo", c[2].node_id), condition,
                        IRFragment(instructions=(Label(end),)),
                    ]))
            else:
                raise AssertionError(kind)
        return combine_fragments(*fragments)

    def _is_until_condition(self, cond_node_id: int) -> bool:
        cond = self._require_node(cond_node_id, NodeKind.INNER, "COND")
        children = self._children(cond)
        if len(children) != 1 or children[0].kind is not NodeKind.LEAF or children[0].contents not in {"while", "until"}:
            raise CodegenError("CODEGEN-COND-SHAPE", "COND must contain while or until.", node_id=cond.node_id)
        return children[0].contents == "until"

    def _emit_call(
        self,
        call_node_id: int,
        destination: StorageLocation | None,
        environment: SymbolEnvironment | None,
    ) -> IRFragment:
        call = self._require_node(call_node_id, NodeKind.INNER, "CALL")
        if self.call_emitter is None:
            raise CodegenError(
                "CODEGEN-CALL-HOOK-MISSING",
                "This valid program contains a function call but no inliner CallEmitter was supplied.",
                node_id=call.node_id,
            )
        fragment = self.call_emitter.emit_call(
            call_node_id,
            destination,
            environment or {},
            self.context,
        )
        if not isinstance(fragment, IRFragment):
            raise CodegenError("CODEGEN-CALL-HOOK-RESULT", "CallEmitter must return an IRFragment.", node_id=call.node_id)
        return fragment

    def _require_node(self, node_id: int, kind: NodeKind, contents: str) -> TreeNode:
        try:
            node = self.tree.get_node(node_id)
        except ValueError as exc:
            raise CodegenError("CODEGEN-NODE", str(exc), node_id=node_id) from exc
        if node.kind is not kind or node.contents != contents:
            raise CodegenError(
                "CODEGEN-NODE-SHAPE",
                f"Expected {kind.value} {contents}, found {node.contents!r}.",
                node_id=node_id,
            )
        return node

    def _children(self, node: TreeNode) -> list[TreeNode]:
        return [self.tree.get_node(child_id) for child_id in node.child_ids]

    def _require_checked_type(self, node: TreeNode, expected: SemanticType) -> None:
        actual = self.checked.type_by_node.get(node.node_id)
        if actual is not expected:
            raise CodegenError(
                "CODEGEN-UNCHECKED-NODE",
                f"Node {node.node_id} must have checked type {expected.value}, found {getattr(actual, 'value', actual)!r}.",
                node_id=node.node_id,
            )


def generate_target(
    checked: CheckedProgram,
    *,
    call_emitter: CallEmitter | None = None,
    context: CodegenContext | None = None,
) -> TargetProgram:
    """Lower a checked whole program's main algorithm into a closed target IR."""
    if not isinstance(checked, CheckedProgram):
        raise CodegenError("CODEGEN-CHECKED-PROGRAM", "generate_target accepts only a CheckedProgram.")
    active_context = context if context is not None else CodegenContext(checked)
    if active_context.checked is not checked and active_context.checked != checked:
        raise CodegenError("CODEGEN-CONTEXT", "Generation context belongs to a different CheckedProgram.")
    tree = checked.resolved.tree
    root = tree.root
    if root is None or root.kind is not NodeKind.ROOT or root.contents != "SPL_PROG" or len(root.child_ids) != 1:
        raise CodegenError("CODEGEN-ROOT", "Checked tree must have one SPL_PROG root and one P child.")
    p_node = tree.get_node(root.child_ids[0])
    if p_node.kind is not NodeKind.INNER or p_node.contents != "P":
        raise CodegenError("CODEGEN-ROOT", "SPL_PROG child must be P.", node_id=p_node.node_id)
    parts = program_parts(tree, p_node.node_id)
    root_scope_id = checked.resolved.scope_by_node[p_node.node_id]
    declared_symbol_ids: list[int] = []
    for leaf in iter_list_items(tree, parts.variables.node_id):
        symbol_id = checked.resolved.binding_by_name_node.get(leaf.node_id)
        if symbol_id is None:
            raise CodegenError("CODEGEN-UNBOUND-DECLARATION", "Variable declaration lacks a symbol binding.", node_id=leaf.node_id)
        symbol = checked.resolved.symbols.get(symbol_id)
        if symbol is None or symbol.kind is not SymbolKind.VARIABLE or symbol.scope_id != root_scope_id:
            raise CodegenError("CODEGEN-DECLARATION-SCOPE", "Root variable declaration has invalid semantic identity.", node_id=leaf.node_id)
        declared_symbol_ids.append(symbol_id)

    generator = CodeGenerator(checked, context=active_context, call_emitter=call_emitter)
    main_fragment = generator.emit_algorithm(parts.algorithm.node_id)
    return TargetProgram(
        numeric_mode=checked.numeric_mode,
        root_scope_id=root_scope_id,
        symbols=checked.resolved.symbols,
        declared_symbol_ids=tuple(declared_symbol_ids),
        fragment=main_fragment,
    )
