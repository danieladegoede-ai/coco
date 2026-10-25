"""Independent reference evaluator for SPL programs.

This is a test-only oracle that evaluates SPL programs independently of the
compiler's code generator. It interprets the syntax tree directly to compute
expected outputs for testing.

Tree structure reference:
- SPL_PROG -> P
- P -> V_DECL : F_DECL : ALGO
- ALGO -> INSTR ; ALGO | empty
- INSTR -> print OUTP | nop | comment STRING | ASSIGN | BRANCH | LOOP | CALL
- ASSIGN -> #name = TERM
- TERM -> #name | NUM | operator ( TERM TERM ) | neg ( TERM ) | CALL
- BOOL -> comparison ( TERM TERM ) | not ( BOOL ) | and/or ( BOOL BOOL )
- LOOP -> COND BOOL do { ALGO } | do { ALGO } COND BOOL
- BRANCH -> if BOOL then { ALGO } else { ALGO }
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode
from spl_frontend.name_analysis import resolve_names
from spl_frontend.type_analysis import check_types


Number = Union[int, float]


@dataclass
class EvalError(Exception):
    """Error during SPL interpretation."""
    message: str
    node_id: int | None = None


@dataclass
class Environment:
    """Runtime environment for SPL execution."""
    variables: dict[str, Number] = field(default_factory=dict)
    functions: dict[str, "FunctionDef"] = field(default_factory=dict)
    parent: Environment | None = None
    max_steps: int = 10000
    steps: int = 0
    budget: list[int] | None = None

    def __post_init__(self) -> None:
        if self.budget is None:
            self.budget = self.parent.budget if self.parent else [0]

    def lookup_var(self, name: str) -> Number:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup_var(name)
        raise EvalError(f"Undefined variable: {name}")

    def assign_var(self, name: str, value: Number) -> None:
        if name in self.variables:
            self.variables[name] = value
        elif self.parent and self._has_var(name):
            self.parent.assign_var(name, value)
        else:
            self.variables[name] = value

    def _has_var(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent:
            return self.parent._has_var(name)
        return False

    def lookup_func(self, name: str) -> "FunctionDef":
        if name in self.functions:
            return self.functions[name]
        raise EvalError(f"Undefined function: {name}")

    def tick(self) -> None:
        assert self.budget is not None
        self.budget[0] += 1
        self.steps = self.budget[0]
        if self.steps > self.max_steps:
            raise EvalError("Execution step limit exceeded")


@dataclass
class FunctionDef:
    """A function definition."""
    name: str
    is_void: bool
    params: list[str]
    body_node_id: int
    return_term_node_id: int | None


class Evaluator:
    """Interprets SPL programs from their syntax tree."""

    def __init__(self, tree: SyntaxTree, numeric_mode: str = "integer"):
        self.tree = tree
        self.numeric_mode = numeric_mode
        self.outputs: list[str] = []

    def evaluate(self, max_steps: int = 10000) -> list[str]:
        """Evaluate the program and return printed outputs."""
        self.outputs = []
        env = Environment(max_steps=max_steps)

        assert self.tree.root is not None
        # SPL_PROG -> P
        p_node = self._child(self.tree.root, 0)
        self._eval_p(p_node, env)
        return self.outputs

    def _child(self, node: TreeNode, index: int) -> TreeNode:
        """Get child node at index."""
        return self.tree.get_node(node.child_ids[index])

    def _child_content(self, node: TreeNode, index: int) -> str:
        """Get content of child at index."""
        return self._child(node, index).contents

    def _eval_p(self, node: TreeNode, env: Environment) -> None:
        """Evaluate P -> V_DECL : F_DECL : ALGO"""
        # P has: V_DECL, :, F_DECL, :, ALGO
        v_decl = self._child(node, 0)
        f_decl = self._child(node, 2)
        algo = self._child(node, 4)

        # Declare variables
        self._collect_vars(v_decl, env)
        # Collect function definitions
        self._collect_funcs(f_decl, env)
        # Execute algorithm
        self._eval_algo(algo, env)

    def _collect_vars(self, node: TreeNode, env: Environment) -> None:
        """Collect variable declarations from V_DECL."""
        while node.child_ids:
            env.variables[self._child_content(node, 0)] = 0
            node = self._child(node, 1)

    def _collect_funcs(self, node: TreeNode, env: Environment) -> None:
        """Collect function definitions from F_DECL."""
        while node.child_ids:
            self._register_func(self._child(node, 0), env)
            node = self._child(node, 1)

    def _register_func(self, f_type: TreeNode, env: Environment) -> None:
        """Register a function from F_TYPE."""
        # F_TYPE -> void/num #name ( V_DECL ) { P return [( TERM )] }
        kind = self._child_content(f_type, 0)  # void or num
        name = self._child_content(f_type, 1)  # #name
        params_node = self._child(f_type, 3)   # V_DECL

        params = []
        self._collect_param_names(params_node, params)

        body_node = self._child(f_type, 6)  # P

        return_term_id = None
        if kind == "num":
            # Find return ( TERM )
            for i, cid in enumerate(f_type.child_ids):
                child = self.tree.get_node(cid)
                if child.contents == "return" and i + 2 < len(f_type.child_ids):
                    term_node = self._child(f_type, i + 2)
                    if term_node.contents == "TERM":
                        return_term_id = term_node.node_id
                    break

        env.functions[name] = FunctionDef(
            name=name,
            is_void=(kind == "void"),
            params=params,
            body_node_id=body_node.node_id,
            return_term_node_id=return_term_id,
        )

    def _collect_param_names(self, v_decl: TreeNode, params: list[str]) -> None:
        """Collect parameter names from V_DECL."""
        while v_decl.child_ids:
            params.append(self._child_content(v_decl, 0))
            v_decl = self._child(v_decl, 1)

    def _eval_algo(self, node: TreeNode, env: Environment) -> None:
        """Evaluate ALGO -> INSTR ; ALGO | empty"""
        while node.child_ids:
            env.tick()
            self._eval_instr(self._child(node, 0), env)
            node = self._child(node, 2)

    def _eval_instr(self, node: TreeNode, env: Environment) -> None:
        """Evaluate an INSTR node."""
        if not node.child_ids:
            return

        first = self._child(node, 0)

        if first.contents == "print":
            self._eval_print(node, env)
        elif first.contents == "nop":
            pass
        elif first.contents == "comment":
            pass
        elif first.contents == "BRANCH":
            self._eval_branch(first, env)
        elif first.contents == "ASSIGN":
            self._eval_assign(first, env)
        elif first.contents == "LOOP":
            self._eval_loop(first, env)
        elif first.contents == "CALL":
            self._eval_call(first, env)

    def _eval_print(self, node: TreeNode, env: Environment) -> None:
        """Evaluate print OUTP."""
        outp = self._child(node, 1)
        first_outp_child = self._child(outp, 0)

        if first_outp_child.contents.startswith('"'):
            # String literal
            text = first_outp_child.contents[1:-1]
            self.outputs.append(text)
        else:
            # ( TERM )
            term = self._child(outp, 1)
            value = self._eval_term(term, env)
            self.outputs.append(self._format_number(value))

    def _format_number(self, value: Number) -> str:
        """Format a number for output."""
        # std::cout's defaultfloat uses six significant digits, including
        # scientific notation for large integral-valued floating numbers.
        return format(value, ".6g") if isinstance(value, float) else str(value)

    def _eval_assign(self, node: TreeNode, env: Environment) -> None:
        """Evaluate ASSIGN -> #name = TERM."""
        var_name = self._child_content(node, 0)
        term = self._child(node, 2)
        value = self._eval_term(term, env)
        env.assign_var(var_name, value)

    def _eval_term(self, node: TreeNode, env: Environment) -> Number:
        """Evaluate a TERM node."""
        if not node.child_ids:
            return 0

        first = self._child(node, 0)

        # Variable reference
        if first.kind == NodeKind.LEAF and re.match(r"#[a-z0-9]*", first.contents):
            # Check if it's a CALL
            if len(node.child_ids) > 1 and self._child_content(node, 1) == "(":
                return self._eval_call(node, env)
            return env.lookup_var(first.contents)

        # Number literal
        if first.kind == NodeKind.LEAF and self._is_number(first.contents):
            return self._parse_number(first.contents)

        # CALL node
        if first.contents == "CALL":
            return self._eval_call(first, env)

        # Operators: op ( TERM [TERM] )
        if first.kind == NodeKind.LEAF and first.contents in ("add", "sub", "mul", "div", "mod", "neg"):
            return self._eval_arith(node, env)

        # Single child that is a TERM
        if first.contents == "TERM":
            return self._eval_term(first, env)

        # Leaf number/variable inside TERM
        if first.kind == NodeKind.LEAF:
            if self._is_number(first.contents):
                return self._parse_number(first.contents)
            if re.match(r"#[a-z0-9]*", first.contents):
                return env.lookup_var(first.contents)

        raise EvalError(f"Cannot evaluate TERM: {node.contents}", node.node_id)

    def _is_number(self, text: str) -> bool:
        """Check if text is a number literal."""
        try:
            float(text)
            return True
        except ValueError:
            return False

    def _parse_number(self, text: str) -> Number:
        """Parse a number literal."""
        return self._stored_number(float(text)) if self.numeric_mode == "float" else int(text)

    def _stored_number(self, value: Number) -> Number:
        """Round at each target float storage boundary, independently of IR.

        The backend deliberately uses C++ float (IEEE binary32), including
        temporary operands and results. Python arithmetic alone is binary64.
        """
        if self.numeric_mode == "float":
            return struct.unpack("=f", struct.pack("=f", float(value)))[0]
        return value

    def _eval_arith(self, node: TreeNode, env: Environment) -> Number:
        """Evaluate arithmetic: op ( TERM [TERM] )."""
        op = self._child_content(node, 0)
        # Children: op, (, TERM, [TERM], )
        if op == "neg":
            operand = self._child(node, 2)
            return self._stored_number(-self._eval_term(operand, env))

        left = self._child(node, 2)
        right = self._child(node, 3)
        left_val = self._eval_term(left, env)
        right_val = self._eval_term(right, env)

        if op == "add":
            return self._stored_number(left_val + right_val)
        if op == "sub":
            return self._stored_number(left_val - right_val)
        if op == "mul":
            return self._stored_number(left_val * right_val)
        if op == "div":
            return self._stored_number(left_val / right_val)
        if op == "mod":
            # C/C++ integer remainder truncates the quotient toward zero.
            a, b = int(left_val), int(right_val)
            q = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                q = -q
            return a - q * b
        raise EvalError(f"Unknown operator: {op}")

    def _eval_call(self, node: TreeNode, env: Environment) -> Number:
        """Evaluate a function CALL."""
        # CALL -> #name ( INPUT )
        func_name = self._child_content(node, 0)
        func = env.lookup_func(func_name)

        # Collect arguments from INPUT
        input_node = self._child(node, 2)
        args = self._collect_args(input_node, env)

        # Create call environment
        call_env = Environment(parent=env, max_steps=env.max_steps)
        call_env.steps = env.steps

        if len(func.params) != len(args):
            raise EvalError("Argument count does not match parameters", node.node_id)
        for param, value in zip(func.params, args):
            call_env.variables[param] = value

        # Execute body
        body = self.tree.get_node(func.body_node_id)
        self._eval_p(body, call_env)

        env.steps = call_env.steps

        if func.is_void:
            return 0

        # Evaluate return term
        assert func.return_term_node_id is not None
        return_term = self.tree.get_node(func.return_term_node_id)
        return self._eval_term(return_term, call_env)

    def _collect_args(self, input_node: TreeNode, env: Environment) -> list[Number]:
        """Collect arguments from INPUT node."""
        args = []
        while input_node.child_ids:
            args.append(self._eval_term(self._child(input_node, 0), env))
            input_node = self._child(input_node, 1)
        return args

    def _eval_branch(self, node: TreeNode, env: Environment) -> None:
        """Evaluate if BOOL then { ALGO } else { ALGO }."""
        # Children: if, BOOL, then, {, ALGO, }, else, {, ALGO, }
        bool_node = self._child(node, 1)
        cond = self._eval_bool(bool_node, env)

        then_algo = self._child(node, 4)
        else_algo = self._child(node, 8)

        if cond:
            self._eval_algo(then_algo, env)
        else:
            self._eval_algo(else_algo, env)

    def _eval_loop(self, node: TreeNode, env: Environment) -> None:
        """Evaluate a LOOP node."""
        first = self._child(node, 0)

        if first.contents == "COND":
            # Pre-test loop: COND BOOL do { ALGO }
            self._eval_pre_loop(node, env)
        elif first.contents == "do":
            # Post-test loop: do { ALGO } COND BOOL
            self._eval_post_loop(node, env)

    def _eval_pre_loop(self, node: TreeNode, env: Environment) -> None:
        """Evaluate while/until BOOL do { ALGO }."""
        # Children: COND, BOOL, do, {, ALGO, }
        cond_node = self._child(node, 0)
        cond_type = self._child_content(cond_node, 0)  # while or until
        bool_node = self._child(node, 1)
        algo_node = self._child(node, 4)

        is_until = (cond_type == "until")

        while True:
            env.tick()
            cond = self._eval_bool(bool_node, env)
            if is_until:
                if cond:
                    break
            else:
                if not cond:
                    break
            self._eval_algo(algo_node, env)

    def _eval_post_loop(self, node: TreeNode, env: Environment) -> None:
        """Evaluate do { ALGO } while/until BOOL."""
        # Children: do, {, ALGO, }, COND, BOOL
        algo_node = self._child(node, 2)
        cond_node = self._child(node, 4)
        cond_type = self._child_content(cond_node, 0)
        bool_node = self._child(node, 5)

        is_until = (cond_type == "until")

        while True:
            env.tick()
            self._eval_algo(algo_node, env)
            cond = self._eval_bool(bool_node, env)
            if is_until:
                if cond:
                    break
            else:
                if not cond:
                    break

    def _eval_bool(self, node: TreeNode, env: Environment) -> bool:
        """Evaluate a BOOL node."""
        if not node.child_ids:
            return False

        first = self._child(node, 0)
        op = first.contents

        if op == "not":
            # not ( BOOL )
            inner = self._child(node, 2)
            return not self._eval_bool(inner, env)

        if op in ("and", "or"):
            # and/or ( BOOL BOOL )
            left = self._child(node, 2)
            right = self._child(node, 3)
            left_val = self._eval_bool(left, env)
            if op == "and":
                return left_val and self._eval_bool(right, env)
            return left_val or self._eval_bool(right, env)

        if op in ("eq", "larger", "lesser"):
            # comparison ( TERM TERM )
            left = self._child(node, 2)
            right = self._child(node, 3)
            left_val = self._eval_term(left, env)
            right_val = self._eval_term(right, env)
            if op == "eq":
                return left_val == right_val
            if op == "larger":
                return left_val > right_val
            return left_val < right_val

        raise EvalError(f"Unknown bool operator: {op}")


def evaluate_source(source: str, max_steps: int = 10000) -> list[str]:
    """Parse and evaluate SPL source code, returning printed outputs."""
    sf = SourceFile(path=Path("eval.spl"), text=source)
    tokens = tokenize(sf)
    tree = SyntaxTree()
    parse(tokens, tree, Path("eval.spl"))
    tree.validate()

    resolved = resolve_names(tree, path=Path("eval.spl"))
    checked = check_types(resolved)

    evaluator = Evaluator(tree=tree, numeric_mode=checked.numeric_mode.value.lower())
    return evaluator.evaluate(max_steps=max_steps)


def evaluate_file(path: Path, max_steps: int = 10000) -> list[str]:
    """Parse and evaluate an SPL file, returning printed outputs."""
    source = path.read_text(encoding="utf-8")
    return evaluate_source(source, max_steps=max_steps)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: reference_spl_evaluator.py <file.spl>")
        sys.exit(1)
    path = Path(sys.argv[1])
    outputs = evaluate_file(path)
    for output in outputs:
        print(output)
