"""Regression checks that generated negative cases are actually invalid SPL."""

from __future__ import annotations

import unittest
from pathlib import Path

from spl_frontend.diagnostics import FrontendError
from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from tools.generate_valid_spl import generate_program
from tools.mutate_spl import MutationKind, mutate_program


class MutationValidityTests(unittest.TestCase):
    def assert_rejected(self, program: str) -> None:
        with self.assertRaises(FrontendError):
            parse(tokenize(SourceFile(Path("SPL.txt"), program)), SyntaxTree())

    def test_truncation_cannot_end_after_complete_nullable_algorithm(self) -> None:
        original = generate_program(seed=7)
        mutation = mutate_program(original, seed=12)
        self.assertEqual(mutation.kind, MutationKind.TRUNCATE)
        self.assert_rejected(mutation.program)

    def test_seeded_mutations_of_generated_programs_are_rejected(self) -> None:
        for source_seed in range(25):
            original = generate_program(seed=source_seed)
            for mutation_seed in range(20):
                with self.subTest(source_seed=source_seed, mutation_seed=mutation_seed):
                    mutation = mutate_program(original, seed=mutation_seed)
                    self.assert_rejected(mutation.program)


if __name__ == "__main__":
    unittest.main()
