"""Part 2b type analysis over resolved SPL programs.

Implements the attribute grammar rules from Prac-Spec-2b to check type
correctness and produce a CheckedProgram for code generation.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from spl_frontend.semantic_model import (
    CheckedProgram, NumericMode, ResolvedProgram, SemanticType, SourceSpan, Symbol, SymbolKind,
)
from spl_frontend.numeric_policy import scan_numeric_policy, NumericPolicyError
from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode
from spl_frontend.tree_walkers import (
    function_parts, iter_postorder, program_parts,
)


class TypeAnalysisError(ValueError):
    """A type violation with location information."""

    def __init__(
        self, code: str, message: str, *, node_id: int,
        expected: SemanticType | None = None,
        actual: SemanticType | None = None,
        path: Path | None = None,
        span: SourceSpan | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.node_id = node_id
        self.expected = expected
        self.actual = actual
        self.path = span.path if span else path
        self.span = span

    def render(self) -> str:
        location = str(self.path) if self.path is not None else "tree"
        if self.span is not None:
            location += f":{self.span.line}:{self.span.column}"
        else:
            location += f":node[{self.node_id}]"
        detail = ""
        if self.expected and self.actual:
            detail = f" (expected {self.expected.value}, got {self.actual.value})"
        return f"{location}: type[{self.code}]: {self.message}{detail}"


class _TypeChecker:
    """Internal state for type checking traversal."""

    def __init__(self, resolved: ResolvedProgram, numeric_mode: NumericMode) -> None:
        self.resolved = resolved
        self.tree = resolved.tree
        self.numeric_mode = numeric_mode
        self.types: dict[int, SemanticType] = {}
        self.symbols: dict[int, Symbol] = dict(resolved.symbols)

    def fail(
        self, code: str, node: TreeNode, message: str,
        expected: SemanticType | None = None,
        actual: SemanticType | None = None,
    ) -> None:
        raise TypeAnalysisError(
            code, message, node_id=node.node_id,
            expected=expected, actual=actual,
            span=self.resolved.source_location_by_node.get(node.node_id),
        )

    def get_type(self, node_id: int) -> SemanticType:
        return self.types.get(node_id, SemanticType.UNKNOWN)

    def set_type(self, node_id: int, typ: SemanticType) -> None:
        self.types[node_id] = typ

    def require(
        self, node: TreeNode, expected: SemanticType, message: str,
    ) -> None:
        actual = self.get_type(node.node_id)
        if actual != expected:
            self.fail(
                "TYPE-MISMATCH", node, message,
                expected=expected, actual=actual,
            )

    def check(self) -> CheckedProgram:
        self._seed_declarations()
        self._check_tree()
        self._validate_root()
        typed_resolved = ResolvedProgram(
            self.resolved.tree,
            self.resolved.scopes,
            self.symbols,
            self.resolved.scope_by_node,
            self.resolved.binding_by_name_node,
            self.resolved.source_location_by_node,
        )
        return CheckedProgram(
            typed_resolved,
            self.types,
            self.numeric_mode,
        )

    def _seed_declarations(self) -> None:
        """Seed all declaration signatures before checking bodies."""
        for symbol in self.resolved.symbols.values():
            if symbol.kind in (SymbolKind.VARIABLE, SymbolKind.PARAMETER):
                self.symbols[symbol.symbol_id] = replace(
                    symbol, value_type=SemanticType.NUMERIC
                )
        for node in self.tree.iter_nodes():
            if node.kind is NodeKind.INNER and node.contents == "F_TYPE":
                parts = function_parts(self.tree, node.node_id)
                name_node = parts.name
                symbol_id = self.resolved.binding_by_name_node[name_node.node_id]
                symbol = self.symbols[symbol_id]
                if parts.return_keyword == "void":
                    new_type = SemanticType.PROCEDURE
                else:
                    new_type = SemanticType.NUMERIC
                self.symbols[symbol_id] = replace(symbol, value_type=new_type)

    def _check_tree(self) -> None:
        """Check types in post-order (children before parents)."""
        for node in iter_postorder(self.tree):
            self._check_node(node)

    def _check_node(self, node: TreeNode) -> None:
        if node.kind is NodeKind.LEAF:
            self._check_leaf(node)
        elif node.kind is NodeKind.ROOT:
            self._check_spl_prog(node)
        else:
            self._check_inner(node)

    def _check_leaf(self, node: TreeNode) -> None:
        contents = node.contents
        if node.node_id in self.resolved.binding_by_name_node:
            symbol_id = self.resolved.binding_by_name_node[node.node_id]
            symbol = self.symbols[symbol_id]
            self.set_type(node.node_id, symbol.value_type)
        elif contents.startswith('"'):
            pass
        elif contents[:1].isdigit() or (contents.startswith("-") and len(contents) > 1):
            self.set_type(node.node_id, SemanticType.NUMERIC)

    def _check_spl_prog(self, node: TreeNode) -> None:
        if not node.child_ids:
            self.fail("TYPE-EMPTY", node, "Program has no P node.")
        p_node = self.tree.get_node(node.child_ids[0])
        if self.get_type(p_node.node_id) == SemanticType.OK:
            self.set_type(node.node_id, SemanticType.OK)
        else:
            self.fail("TYPE-PROGRAM", node, "Program P is not ok.")

    def _check_inner(self, node: TreeNode) -> None:
        contents = node.contents
        if contents == "P":
            self._check_p(node)
        elif contents == "V_DECL":
            self._check_v_decl(node)
        elif contents == "F_DECL":
            self._check_f_decl(node)
        elif contents == "F_TYPE":
            self._check_f_type(node)
        elif contents == "ALGO":
            self._check_algo(node)
        elif contents == "INSTR":
            self._check_instr(node)
        elif contents == "OUTP":
            self._check_outp(node)
        elif contents == "ASSIGN":
            self._check_assign(node)
        elif contents == "CALL":
            self._check_call(node)
        elif contents == "INPUT":
            self._check_input(node)
        elif contents == "TERM":
            self._check_term(node)
        elif contents == "BRANCH":
            self._check_branch(node)
        elif contents == "LOOP":
            self._check_loop(node)
        elif contents == "BOOL":
            self._check_bool(node)
        elif contents == "COND":
            self._check_cond(node)

    def _check_p(self, node: TreeNode) -> None:
        parts = program_parts(self.tree, node.node_id)
        v_ok = self.get_type(parts.variables.node_id) == SemanticType.OK
        f_ok = self.get_type(parts.functions.node_id) == SemanticType.OK
        a_ok = self.get_type(parts.algorithm.node_id) == SemanticType.OK
        if v_ok and f_ok and a_ok:
            self.set_type(node.node_id, SemanticType.OK)
        else:
            if not v_ok:
                self.fail("TYPE-P-VDECL", node, "V_DECL is not ok.")
            if not f_ok:
                self.fail("TYPE-P-FDECL", node, "F_DECL is not ok.")
            if not a_ok:
                self.fail("TYPE-P-ALGO", node, "ALGO is not ok.")

    def _check_v_decl(self, node: TreeNode) -> None:
        if not node.child_ids:
            self.set_type(node.node_id, SemanticType.OK)
            return
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if len(children) == 2:
            name_node, tail = children
            if name_node.node_id in self.resolved.binding_by_name_node:
                symbol_id = self.resolved.binding_by_name_node[name_node.node_id]
                self.symbols[symbol_id] = replace(
                    self.symbols[symbol_id], value_type=SemanticType.NUMERIC
                )
            if self.get_type(tail.node_id) == SemanticType.OK:
                self.set_type(node.node_id, SemanticType.OK)
            else:
                self.fail("TYPE-VDECL", node, "V_DECL tail is not ok.")

    def _check_f_decl(self, node: TreeNode) -> None:
        if not node.child_ids:
            self.set_type(node.node_id, SemanticType.OK)
            return
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if len(children) == 2:
            f_type, tail = children
            if self.get_type(f_type.node_id) == SemanticType.OK and \
               self.get_type(tail.node_id) == SemanticType.OK:
                self.set_type(node.node_id, SemanticType.OK)
            else:
                self.fail("TYPE-FDECL", node, "F_DECL component is not ok.")

    def _check_f_type(self, node: TreeNode) -> None:
        parts = function_parts(self.tree, node.node_id)
        p_node = parts.body
        v_decl = parts.parameters
        p_ok = self.get_type(p_node.node_id) == SemanticType.OK
        v_ok = self.get_type(v_decl.node_id) == SemanticType.OK
        name_node = parts.name
        symbol_id = self.resolved.binding_by_name_node[name_node.node_id]
        if parts.return_keyword == "void":
            if p_ok and v_ok:
                self.symbols[symbol_id] = replace(
                    self.symbols[symbol_id], value_type=SemanticType.PROCEDURE
                )
                self.set_type(node.node_id, SemanticType.OK)
            else:
                self.fail("TYPE-VOID-FUNC", node, "Void function body or params not ok.")
        else:
            return_term = parts.return_term
            assert return_term is not None
            term_ok = self.get_type(return_term.node_id) == SemanticType.NUMERIC
            if p_ok and v_ok and term_ok:
                self.symbols[symbol_id] = replace(
                    self.symbols[symbol_id], value_type=SemanticType.NUMERIC
                )
                self.set_type(node.node_id, SemanticType.OK)
            else:
                if not term_ok:
                    self.fail(
                        "TYPE-RETURN", node,
                        "Return TERM must be numeric.",
                        expected=SemanticType.NUMERIC,
                        actual=self.get_type(return_term.node_id),
                    )
                else:
                    self.fail("TYPE-NUM-FUNC", node, "Num function body or params not ok.")

    def _check_algo(self, node: TreeNode) -> None:
        if not node.child_ids:
            self.set_type(node.node_id, SemanticType.OK)
            return
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if len(children) == 3:
            instr, _, tail = children
            if self.get_type(instr.node_id) == SemanticType.OK and \
               self.get_type(tail.node_id) == SemanticType.OK:
                self.set_type(node.node_id, SemanticType.OK)
            else:
                if self.get_type(instr.node_id) != SemanticType.OK:
                    self.fail("TYPE-ALGO-INSTR", node, "INSTR is not ok.")
                else:
                    self.fail("TYPE-ALGO-TAIL", node, "ALGO tail is not ok.")

    def _check_instr(self, node: TreeNode) -> None:
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if not children:
            self.fail("TYPE-INSTR-EMPTY", node, "INSTR has no children.")
            return
        first = children[0]
        if first.kind is NodeKind.LEAF:
            if first.contents == "print":
                outp = children[1]
                if self.get_type(outp.node_id) == SemanticType.OK:
                    self.set_type(node.node_id, SemanticType.OK)
                else:
                    self.fail("TYPE-PRINT", node, "print OUTP is not ok.")
            elif first.contents == "nop":
                self.set_type(node.node_id, SemanticType.OK)
            elif first.contents == "comment":
                self.set_type(node.node_id, SemanticType.OK)
        elif first.kind is NodeKind.INNER:
            if first.contents == "ASSIGN":
                if self.get_type(first.node_id) == SemanticType.OK:
                    self.set_type(node.node_id, SemanticType.OK)
                else:
                    self.fail("TYPE-INSTR-ASSIGN", node, "ASSIGN is not ok.")
            elif first.contents == "BRANCH":
                if self.get_type(first.node_id) == SemanticType.OK:
                    self.set_type(node.node_id, SemanticType.OK)
                else:
                    self.fail("TYPE-INSTR-BRANCH", node, "BRANCH is not ok.")
            elif first.contents == "LOOP":
                if self.get_type(first.node_id) == SemanticType.OK:
                    self.set_type(node.node_id, SemanticType.OK)
                else:
                    self.fail("TYPE-INSTR-LOOP", node, "LOOP is not ok.")
            elif first.contents == "CALL":
                call_type = self.get_type(first.node_id)
                if call_type == SemanticType.PROCEDURE:
                    self.set_type(node.node_id, SemanticType.OK)
                else:
                    self.fail(
                        "TYPE-INSTR-CALL", node,
                        "INSTR CALL must be a procedure (void function).",
                        expected=SemanticType.PROCEDURE,
                        actual=call_type,
                    )

    def _check_outp(self, node: TreeNode) -> None:
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if children and children[0].kind is NodeKind.LEAF:
            if children[0].contents.startswith('"'):
                self.set_type(node.node_id, SemanticType.OK)
                return
        if len(children) == 3:
            term = children[1]
            if self.get_type(term.node_id) == SemanticType.NUMERIC:
                self.set_type(node.node_id, SemanticType.OK)
            else:
                self.fail(
                    "TYPE-OUTP", node,
                    "OUTP TERM must be numeric.",
                    expected=SemanticType.NUMERIC,
                    actual=self.get_type(term.node_id),
                )

    def _check_assign(self, node: TreeNode) -> None:
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if len(children) != 3:
            self.fail("TYPE-ASSIGN-SHAPE", node, "ASSIGN requires NAME = TERM.")
            return
        name_node, _, term = children
        name_type = self.get_type(name_node.node_id)
        term_type = self.get_type(term.node_id)
        if name_type == SemanticType.NUMERIC and term_type == SemanticType.NUMERIC:
            self.set_type(node.node_id, SemanticType.OK)
        else:
            if name_type != SemanticType.NUMERIC:
                self.fail(
                    "TYPE-ASSIGN-NAME", node,
                    "Assignment target must be numeric.",
                    expected=SemanticType.NUMERIC,
                    actual=name_type,
                )
            else:
                self.fail(
                    "TYPE-ASSIGN-TERM", node,
                    "Assignment value must be numeric.",
                    expected=SemanticType.NUMERIC,
                    actual=term_type,
                )

    def _check_call(self, node: TreeNode) -> None:
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if len(children) < 3:
            self.fail("TYPE-CALL-SHAPE", node, "CALL requires NAME ( INPUT ).")
            return
        name_node = children[0]
        input_node = children[2]
        if self.get_type(input_node.node_id) != SemanticType.OK:
            self.fail("TYPE-CALL-INPUT", node, "CALL INPUT is not ok.")
            return
        symbol_id = self.resolved.binding_by_name_node.get(name_node.node_id)
        if symbol_id is None:
            self.fail("TYPE-CALL-UNBOUND", node, "CALL name is not bound.")
            return
        symbol = self.symbols[symbol_id]
        if symbol.value_type == SemanticType.UNKNOWN:
            self.fail("TYPE-CALL-UNKNOWN", node, "CALL function type is unknown.")
            return
        self.set_type(node.node_id, symbol.value_type)

    def _check_input(self, node: TreeNode) -> None:
        if not node.child_ids:
            self.set_type(node.node_id, SemanticType.OK)
            return
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if len(children) == 2:
            term, tail = children
            term_type = self.get_type(term.node_id)
            tail_type = self.get_type(tail.node_id)
            if term_type == SemanticType.NUMERIC and tail_type == SemanticType.OK:
                self.set_type(node.node_id, SemanticType.OK)
            else:
                if term_type != SemanticType.NUMERIC:
                    self.fail(
                        "TYPE-INPUT-TERM", node,
                        "INPUT TERM must be numeric.",
                        expected=SemanticType.NUMERIC,
                        actual=term_type,
                    )
                else:
                    self.fail("TYPE-INPUT-TAIL", node, "INPUT tail is not ok.")

    def _check_term(self, node: TreeNode) -> None:
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if not children:
            self.fail("TYPE-TERM-EMPTY", node, "TERM has no children.")
            return
        first = children[0]
        if first.kind is NodeKind.LEAF:
            if first.node_id in self.resolved.binding_by_name_node:
                symbol_id = self.resolved.binding_by_name_node[first.node_id]
                symbol = self.symbols[symbol_id]
                if symbol.value_type == SemanticType.NUMERIC:
                    self.set_type(node.node_id, SemanticType.NUMERIC)
                else:
                    self.fail(
                        "TYPE-TERM-NAME", node,
                        "TERM NAME must be numeric.",
                        expected=SemanticType.NUMERIC,
                        actual=symbol.value_type,
                    )
            elif first.contents[:1].isdigit() or (first.contents.startswith("-") and len(first.contents) > 1):
                self.set_type(node.node_id, SemanticType.NUMERIC)
            elif first.contents in ("mod", "div", "add", "sub", "mul", "neg"):
                self._check_term_operator(node, first.contents, children)
        elif first.kind is NodeKind.INNER and first.contents == "CALL":
            call_type = self.get_type(first.node_id)
            if call_type == SemanticType.NUMERIC:
                self.set_type(node.node_id, SemanticType.NUMERIC)
            else:
                self.fail(
                    "TYPE-TERM-CALL", node,
                    "TERM CALL must be numeric (num function).",
                    expected=SemanticType.NUMERIC,
                    actual=call_type,
                )

    def _check_term_operator(self, node: TreeNode, op: str, children: list[TreeNode]) -> None:
        if op == "neg":
            if len(children) < 4:
                self.fail("TYPE-TERM-NEG-SHAPE", node, "neg requires ( TERM ).")
                return
            operand = children[2]
            if self.get_type(operand.node_id) == SemanticType.NUMERIC:
                self.set_type(node.node_id, SemanticType.NUMERIC)
            else:
                self.fail(
                    "TYPE-TERM-NEG", node,
                    "neg operand must be numeric.",
                    expected=SemanticType.NUMERIC,
                    actual=self.get_type(operand.node_id),
                )
        else:
            if len(children) < 5:
                self.fail(f"TYPE-TERM-{op.upper()}-SHAPE", node, f"{op} requires ( TERM TERM ).")
                return
            left = children[2]
            right = children[3]
            left_type = self.get_type(left.node_id)
            right_type = self.get_type(right.node_id)
            if left_type == SemanticType.NUMERIC and right_type == SemanticType.NUMERIC:
                self.set_type(node.node_id, SemanticType.NUMERIC)
            else:
                self.fail(
                    f"TYPE-TERM-{op.upper()}", node,
                    f"{op} operands must be numeric.",
                    expected=SemanticType.NUMERIC,
                    actual=left_type if left_type != SemanticType.NUMERIC else right_type,
                )

    def _check_branch(self, node: TreeNode) -> None:
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        bool_node = None
        algo1 = None
        algo2 = None
        for i, child in enumerate(children):
            if child.contents == "BOOL":
                bool_node = child
            elif child.contents == "ALGO":
                if algo1 is None:
                    algo1 = child
                else:
                    algo2 = child
        if bool_node is None or algo1 is None or algo2 is None:
            self.fail("TYPE-BRANCH-SHAPE", node, "BRANCH requires if BOOL then { ALGO } else { ALGO }.")
            return
        bool_ok = self.get_type(bool_node.node_id) == SemanticType.BOOLEAN
        algo1_ok = self.get_type(algo1.node_id) == SemanticType.OK
        algo2_ok = self.get_type(algo2.node_id) == SemanticType.OK
        if bool_ok and algo1_ok and algo2_ok:
            self.set_type(node.node_id, SemanticType.OK)
        else:
            if not bool_ok:
                self.fail(
                    "TYPE-BRANCH-BOOL", node,
                    "BRANCH BOOL must be boolean.",
                    expected=SemanticType.BOOLEAN,
                    actual=self.get_type(bool_node.node_id),
                )
            elif not algo1_ok:
                self.fail("TYPE-BRANCH-THEN", node, "BRANCH then ALGO is not ok.")
            else:
                self.fail("TYPE-BRANCH-ELSE", node, "BRANCH else ALGO is not ok.")

    def _check_loop(self, node: TreeNode) -> None:
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        cond_node = None
        bool_node = None
        algo_node = None
        for child in children:
            if child.contents == "COND":
                cond_node = child
            elif child.contents == "BOOL":
                bool_node = child
            elif child.contents == "ALGO":
                algo_node = child
        if cond_node is None or bool_node is None or algo_node is None:
            self.fail("TYPE-LOOP-SHAPE", node, "LOOP requires COND BOOL do { ALGO } or do { ALGO } COND BOOL.")
            return
        cond_ok = self.get_type(cond_node.node_id) == SemanticType.OK
        bool_ok = self.get_type(bool_node.node_id) == SemanticType.BOOLEAN
        algo_ok = self.get_type(algo_node.node_id) == SemanticType.OK
        if cond_ok and bool_ok and algo_ok:
            self.set_type(node.node_id, SemanticType.OK)
        else:
            if not bool_ok:
                self.fail(
                    "TYPE-LOOP-BOOL", node,
                    "LOOP BOOL must be boolean.",
                    expected=SemanticType.BOOLEAN,
                    actual=self.get_type(bool_node.node_id),
                )
            elif not algo_ok:
                self.fail("TYPE-LOOP-ALGO", node, "LOOP ALGO is not ok.")
            else:
                self.fail("TYPE-LOOP-COND", node, "LOOP COND is not ok.")

    def _check_bool(self, node: TreeNode) -> None:
        children = [self.tree.get_node(cid) for cid in node.child_ids]
        if not children:
            self.fail("TYPE-BOOL-EMPTY", node, "BOOL has no children.")
            return
        first = children[0]
        if first.kind is NodeKind.LEAF:
            op = first.contents
            if op == "not":
                if len(children) < 4:
                    self.fail("TYPE-BOOL-NOT-SHAPE", node, "not requires ( BOOL ).")
                    return
                inner = children[2]
                if self.get_type(inner.node_id) == SemanticType.BOOLEAN:
                    self.set_type(node.node_id, SemanticType.BOOLEAN)
                else:
                    self.fail(
                        "TYPE-BOOL-NOT", node,
                        "not operand must be boolean.",
                        expected=SemanticType.BOOLEAN,
                        actual=self.get_type(inner.node_id),
                    )
            elif op in ("and", "or"):
                if len(children) < 5:
                    self.fail(f"TYPE-BOOL-{op.upper()}-SHAPE", node, f"{op} requires ( BOOL BOOL ).")
                    return
                left = children[2]
                right = children[3]
                if self.get_type(left.node_id) == SemanticType.BOOLEAN and \
                   self.get_type(right.node_id) == SemanticType.BOOLEAN:
                    self.set_type(node.node_id, SemanticType.BOOLEAN)
                else:
                    self.fail(
                        f"TYPE-BOOL-{op.upper()}", node,
                        f"{op} operands must be boolean.",
                        expected=SemanticType.BOOLEAN,
                    )
            elif op in ("eq", "larger", "lesser"):
                if len(children) < 5:
                    self.fail(f"TYPE-BOOL-{op.upper()}-SHAPE", node, f"{op} requires ( TERM TERM ).")
                    return
                left = children[2]
                right = children[3]
                if self.get_type(left.node_id) == SemanticType.NUMERIC and \
                   self.get_type(right.node_id) == SemanticType.NUMERIC:
                    self.set_type(node.node_id, SemanticType.BOOLEAN)
                else:
                    self.fail(
                        f"TYPE-BOOL-{op.upper()}", node,
                        f"{op} operands must be numeric.",
                        expected=SemanticType.NUMERIC,
                    )

    def _check_cond(self, node: TreeNode) -> None:
        self.set_type(node.node_id, SemanticType.OK)

    def _validate_root(self) -> None:
        root = self.tree.root
        assert root is not None
        if self.get_type(root.node_id) != SemanticType.OK:
            raise TypeAnalysisError(
                "TYPE-ROOT", "Program root is not ok.",
                node_id=root.node_id,
            )


def check_types(resolved: ResolvedProgram) -> CheckedProgram:
    """Type-check a resolved program and return a CheckedProgram.

    First runs the numeric policy scan, then checks all type rules.
    """
    try:
        scan_result = scan_numeric_policy(resolved.tree)
        numeric_mode = scan_result.mode
    except NumericPolicyError as exc:
        raise TypeAnalysisError(
            exc.code, exc.message, node_id=exc.node_id or 1,
            span=resolved.source_location_by_node.get(exc.node_id),
        ) from exc

    checker = _TypeChecker(resolved, numeric_mode)
    return checker.check()
