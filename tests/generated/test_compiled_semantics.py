"""Full CLI targets compared with hand facts and an independent evaluator."""
import unittest

from tools.generate_semantic_spl import generate_coverage_program
from tools.reference_spl_evaluator import evaluate_source
from tools.test_generated_target import verify_case
from tests.codegen_support import TARGET_CXX


@unittest.skipUnless(TARGET_CXX, "C++ compiler required for target execution")
class CompiledSemanticTests(unittest.TestCase):
    def assert_case(self, source, expected, case_id, seed=None):
        self.assertEqual("".join(evaluate_source(source)), expected)
        report = verify_case(source, expected, case_id=case_id, seed=seed,
                             target_compiler=TARGET_CXX)
        self.assertTrue(report.passed, report.to_json())

    def test_seeded_complete_programs_match_model_oracle_and_full_cli(self):
        for mode in ("integer", "float"):
            for seed in (0, 1, 7, 42, 341, 2026, 20261024, 0xFFFFFFFF):
                with self.subTest(mode=mode, seed=seed):
                    source, events = generate_coverage_program(seed, mode)
                    self.assert_case(source, "".join(events), f"{mode}-{seed}", seed)

    def test_hand_checked_precision_remainder_and_short_circuit_anchors(self):
        cases = [
            (': : print ( mod ( -5 2 ) ) ; print ":" ; print ( mod ( 5 -2 ) ) ; ', '-1:1'),
            (': : print ( sub ( add ( 16777216 1 ) 16777216 ) ) ; print ( 0.1 ) ; print ( 100000000 ) ; ', '00.11e+08'),
            (': : if eq ( add ( 0.1 0.2 ) 0.3 ) then { print "yes" ; } else { print "no" ; } ; ', 'yes'),
            (': : if eq ( 0 0.0000000001 ) then { print "bad" ; } else { print "exact" ; } ; ', 'exact'),
            ('#x : num #tick ( ) { : : #x = add ( #x 1 ) ; return ( #x ) } : #x = 0 ; '
             'if and ( eq ( 1 2 ) eq ( #tick ( ) 1 ) ) then { } else { } ; '
             'if or ( eq ( 1 1 ) eq ( #tick ( ) 1 ) ) then { } else { } ; print ( #x ) ; ', '0'),
        ]
        for index, (source, expected) in enumerate(cases):
            with self.subTest(index=index):
                self.assert_case(source, expected, f"hand-{index}")
