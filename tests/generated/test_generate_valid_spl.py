"""Independent bounds for the forward SPL test-program generator."""

from __future__ import annotations

import unittest
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import NodeKind, SyntaxTree
from tools.generate_valid_spl import (
    generate_coverage_program, generate_program, generate_to_file, main,
)


def tree_for(program: str) -> SyntaxTree:
    return parse(tokenize(SourceFile(Path("SPL.txt"), program)), SyntaxTree())


class GeneratorBoundsTests(unittest.TestCase):
    def test_max_nodes_is_an_actual_tree_node_cap(self) -> None:
        for seed in range(40):
            with self.subTest(seed=seed):
                program = generate_program(seed=seed, max_nodes=20)
                self.assertLessEqual(len(tree_for(program)), 20)

    def test_impossible_node_cap_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 7"):
            generate_program(seed=1, max_nodes=6)

    def test_minimum_node_cap_produces_minimal_program(self) -> None:
        for seed in range(20):
            with self.subTest(seed=seed):
                program = generate_program(seed=seed, max_nodes=7)
                self.assertEqual(program, ": : ")
                self.assertEqual(len(tree_for(program)), 7)

    def test_expansion_budget_bounds_instruction_count(self) -> None:
        for size in range(10):
            for seed in range(10):
                with self.subTest(size=size, seed=seed):
                    program = generate_program(seed=seed, max_size=size)
                    self.assertLessEqual(program.split().count(";"), size)

    def test_expansion_budget_and_node_cap_are_independent(self) -> None:
        program = generate_program(seed=1, max_size=1, max_nodes=10)
        self.assertLessEqual(len(tree_for(program)), 10)

    def test_same_seed_and_bounds_produce_identical_programs(self) -> None:
        first = generate_program(seed=27, max_size=40, max_nodes=50)
        second = generate_program(seed=27, max_size=40, max_nodes=50)
        self.assertEqual(first, second)

    def test_invalid_bounds_are_rejected(self) -> None:
        for kwargs in ({"max_depth": -1}, {"max_size": -1},
                       {"max_nodes": True}, {"max_nodes": 6}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                generate_program(**kwargs)

    def test_coverage_mode_writes_parseable_program_to_requested_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.spl"
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--coverage", str(path)]), 0)
            self.assertEqual(path.read_text(encoding="ascii"), generate_coverage_program())
            tree_for(path.read_text(encoding="ascii")).validate()

    def test_file_writer_forwards_node_cap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bounded.spl"
            generate_to_file(path, seed=4, max_nodes=7)
            self.assertEqual(path.read_text(encoding="ascii"), ": : ")

    def test_deterministic_coverage_program_exercises_every_production(self) -> None:
        program = generate_coverage_program()
        self.assertEqual(program, generate_coverage_program())
        tree = tree_for(program)
        variants: dict[str, set[tuple[str, ...]]] = {}
        for node in tree.iter_nodes():
            if node.kind is NodeKind.INNER:
                variants.setdefault(node.contents, set()).add(
                    tuple(tree.get_node(child_id).contents for child_id in node.child_ids)
                )
        self.assertEqual(
            set(variants),
            {"P", "V_DECL", "F_DECL", "F_TYPE", "ALGO", "INSTR", "OUTP",
             "CALL", "INPUT", "ASSIGN", "TERM", "BRANCH", "BOOL", "LOOP", "COND"},
        )
        for nullable in ("V_DECL", "F_DECL", "ALGO", "INPUT"):
            self.assertIn((), variants[nullable])
            self.assertTrue(any(children for children in variants[nullable]))
        self.assertEqual({v[0] for v in variants["F_TYPE"]}, {"void", "num"})
        self.assertEqual(
            {v[0] for v in variants["INSTR"]},
            {"print", "nop", "comment", "ASSIGN", "BRANCH", "LOOP", "CALL"},
        )
        self.assertEqual({v[0] for v in variants["OUTP"]}, {'"a"', "("})
        self.assertEqual(
            {v[0] for v in variants["TERM"]},
            {"#x", "#y", "0", "1", "2", "CALL", "mod", "add", "sub", "mul",
             "div", "neg"},
        )
        self.assertEqual(
            {v[0] for v in variants["BOOL"]},
            {"not", "and", "or", "eq", "larger", "lesser"},
        )
        self.assertEqual({v[0] for v in variants["LOOP"]}, {"COND", "do"})
        self.assertEqual({v[0] for v in variants["COND"]}, {"while", "until"})
        leaves = [node.contents for node in tree.iter_nodes()
                  if node.kind is NodeKind.LEAF]
        self.assertEqual(leaves, program.split())
        self.assertNotIn("$", leaves)


if __name__ == "__main__":
    unittest.main()
