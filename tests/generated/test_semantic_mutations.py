"""Each deliberate semantic fault still parses and reaches its intended rule."""
import unittest
from pathlib import Path
from tools.generate_semantic_spl import generate_semantic_program
from tools.mutate_semantic_spl import generate_mutation, MutationType
from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.name_analysis import resolve_names, NameAnalysisError
from spl_frontend.type_analysis import check_types, TypeAnalysisError

class SemanticMutationTests(unittest.TestCase):
    def test_every_mutator_reaches_expected_rule(self):
        for seed in range(12):
            source, _ = generate_semantic_program(seed=seed)
            for kind in MutationType.__args__:
                with self.subTest(seed=seed, kind=kind):
                    mutation = generate_mutation(source, kind, seed)
                    self.assertIsNotNone(mutation)
                    tree = SyntaxTree()
                    parse(tokenize(SourceFile(Path("fault.spl"), mutation.mutated_source)), tree)
                    with self.assertRaises((NameAnalysisError, TypeAnalysisError)) as caught:
                        check_types(resolve_names(tree))
                    self.assertEqual(caught.exception.code, mutation.expected_code)
                    self.assertEqual(mutation.seed, seed)
                    self.assertEqual(generate_mutation(source, kind, seed), mutation)

    def test_strings_are_never_mutated_as_operator_substrings(self):
        source = ': : print "moddiv5.5" ; '
        for kind in MutationType.__args__:
            mutation = generate_mutation(source, kind)
            self.assertIn('"moddiv5.5"', mutation.mutated_source)

    def test_decimal_mod_refuses_independent_div_conflict(self):
        self.assertIsNone(generate_mutation(': : print ( div ( 5 2 ) ) ; ', 'numeric_decimal_mod'))
