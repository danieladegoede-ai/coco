"""Short-circuit Boolean lowering using explicit true/false label transfers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from spl_frontend.codegen_ir import (
    CodegenError,
    CompareOperator,
    ConditionalJump,
    IRFragment,
    Label,
    LabelRef,
    StorageLocation,
    StorageRef,
    SymbolRef,
    combine_fragments,
)
from spl_frontend.semantic_model import CheckedProgram, SemanticType
from spl_frontend.tree import NodeKind, TreeNode


SymbolEnvironment = Mapping[int, StorageLocation]


class BooleanContext(Protocol):
    """Small common allocation/semantic interface used by Boolean lowering."""

    checked: CheckedProgram

    def new_temp(self) -> StorageRef: ...

    def new_label(self) -> LabelRef: ...


class TermEmitter(Protocol):
    def __call__(
        self,
        term_node_id: int,
        destination: StorageLocation,
        environment: SymbolEnvironment | None = None,
    ) -> IRFragment: ...


class BooleanCodeGenerator:
    """Lower BOOL so control reaches ``true_label`` iff its value is true.

    The lowering only emits primitive comparisons, labels and goto instructions;
    it never relies on C++ ``&&``, ``||``, ``!`` or ``else``. ``and`` and ``or``
    short-circuit by routing control to the RHS only when required (the proposed
    D03/D04 policy in the task packet, kept explicit for tutor review).
    """

    def __init__(self, context: BooleanContext, emit_term: TermEmitter) -> None:
        self.context = context
        self.checked = context.checked
        self.tree = self.checked.resolved.tree
        self._emit_term = emit_term

    def emit_bool(
        self,
        bool_node_id: int,
        true_label: LabelRef,
        false_label: LabelRef,
        environment: SymbolEnvironment | None = None,
    ) -> IRFragment:
        tasks = [(bool_node_id, true_label, false_label)]
        fragments = []
        while tasks:
            task = tasks.pop()
            if isinstance(task, IRFragment):
                fragments.append(task)
                continue
            node_id, yes, no = task
            node = self._require_bool_node(node_id)
            if self.checked.type_by_node.get(node_id) is not SemanticType.BOOLEAN:
                raise CodegenError("CODEGEN-UNCHECKED-NODE", "BOOL must have checked Boolean type.", node_id=node_id)
            children = [self.tree.get_node(child_id) for child_id in node.child_ids]
            if not children or children[0].kind is not NodeKind.LEAF:
                raise CodegenError("CODEGEN-BOOL-SHAPE", "Invalid BOOL production.", node_id=node_id)
            operator = children[0].contents
            if operator == "not" and len(children) == 4 and children[2].contents == "BOOL":
                tasks.append((children[2].node_id, no, yes))
            elif operator in {"and", "or"} and len(children) == 5 and all(c.contents == "BOOL" for c in children[2:4]):
                rhs = self.context.new_label()
                tasks.extend(((children[3].node_id, yes, no), IRFragment(instructions=(Label(rhs),)),
                              (children[2].node_id, rhs if operator == "and" else yes,
                               no if operator == "and" else rhs)))
            elif operator in {"eq", "larger", "lesser"} and len(children) == 5 and all(c.contents == "TERM" for c in children[2:4]):
                left, right = self.context.new_temp(), self.context.new_temp()
                fragments.extend((IRFragment(declarations=(left, right)),
                                  self._emit_term(children[2].node_id, left, environment),
                                  self._emit_term(children[3].node_id, right, environment),
                                  IRFragment(instructions=(ConditionalJump(left, CompareOperator.from_spl(operator), right, yes, no),))))
            else:
                raise CodegenError("CODEGEN-BOOL-SHAPE", "Unsupported BOOL production.", node_id=node_id)
        return combine_fragments(*fragments)

    def _require_bool_node(self, node_id: int) -> TreeNode:
        try:
            node = self.tree.get_node(node_id)
        except ValueError as exc:
            raise CodegenError("CODEGEN-NODE", str(exc), node_id=node_id) from exc
        if node.kind is not NodeKind.INNER or node.contents != "BOOL":
            raise CodegenError(
                "CODEGEN-NODE-SHAPE",
                f"Expected inner BOOL node, found {node.contents!r}.",
                node_id=node_id,
            )
        return node
