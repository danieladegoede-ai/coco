"""Native target execution tests for the arithmetic/simple-instruction pass."""

import unittest

from tests.codegen_support import TARGET_CXX, run_source


@unittest.skipUnless(TARGET_CXX, "a C++ compiler is required for executable codegen tests")
class CodegenArithmeticIntegrationTests(unittest.TestCase):
    def test_float_arithmetic_and_mode_selected_by_an_uncalled_body(self):
        run_source(
            ': : print ( add ( 1.5 2 ) ) ; print ":" ; '
            'print ( sub ( mul ( 2.5 4 ) neg ( 3 ) ) ) ; ', "3.5:13",
        )
        # The whole-program mode comes from the checked snapshot, including
        # uncalled declarations. Main contains integer-looking literals only.
        target = run_source(
            ': num #unused ( ) { : : return ( div ( 1 2 ) ) } : '
            'print ( add ( 2 3 ) ) ; print ( sub ( 2 3 ) ) ; print ( mul ( 2 3 ) ) ; ', "5-16",
        )
        self.assertIn("float spl_tmp_", target)

    def test_real_number_storage_uses_binary32_rounding(self):
        # 2**24 + 1 rounds back to 2**24 in float, while double retains it.
        run_source(': : print ( sub ( add ( 16777216.1 1 ) 16777216.1 ) ) ; ', "0")

    def test_issue_arithmetic_anchor_matrix(self):
        # Separate sources keep mod and div in their globally required numeric modes.
        cases = (
            (": : print ( add ( 2 3 ) ) ; ", "5"),
            (": : print ( sub ( 2 3 ) ) ; ", "-1"),
            (": : print ( mul ( 2 3 ) ) ; ", "6"),
            (": : print ( div ( 5 2 ) ) ; ", "2.5"),
            (": : print ( mod ( 5 2 ) ) ; ", "1"),
            (": : print ( neg ( 3 ) ) ; ", "-3"),
            (": : print ( add ( 1 mul ( 2 3 ) ) ) ; ", "7"),
            ("#x : : #x = 8 ; #x = sub ( #x 3 ) ; print ( #x ) ; ", "5"),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                run_source(source, expected)

    def test_prints_concatenate_without_added_whitespace_or_newlines(self):
        run_source(': : print "alpha" ; print "" ; print ( add ( 1 2 ) ) ; print "omega" ; ', "alpha3omega")

    def test_comments_do_not_interfere_with_executable_output(self):
        run_source(': : comment "elsenotaddmul-x" ; print "pass" ; nop ; ', "pass")
