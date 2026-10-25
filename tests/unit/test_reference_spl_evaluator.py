"""Tests for the reference SPL evaluator (independent oracle)."""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from reference_spl_evaluator import evaluate_source, Evaluator, Environment, EvalError


class TestEvaluatorBasicPrint(unittest.TestCase):
    """Test basic print operations."""

    def test_print_string(self):
        source = ': : print "hello" ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["hello"])

    def test_print_multiple_strings(self):
        source = ': : print "a" ; print "b" ; print "c" ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["a", "b", "c"])

    def test_print_numeric_literal(self):
        source = '#x : : #x = 5 ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["5"])


class TestEvaluatorArithmetic(unittest.TestCase):
    """Test arithmetic operations."""

    def test_add(self):
        source = '#x : : #x = add ( 5 3 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["8"])

    def test_sub(self):
        source = '#x : : #x = sub ( 10 3 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["7"])

    def test_mul(self):
        source = '#x : : #x = mul ( 4 5 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["20"])

    def test_div(self):
        source = '#x : : #x = div ( 5 2 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["2.5"])

    def test_mod(self):
        source = '#x : : #x = mod ( 17 5 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["2"])

    def test_neg(self):
        source = '#x : : #x = neg ( 5 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["-5"])

    def test_nested_arithmetic(self):
        source = '#x : : #x = add ( mul ( 2 3 ) sub ( 10 5 ) ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["11"])


class TestEvaluatorBranching(unittest.TestCase):
    """Test conditional branching."""

    def test_if_true_branch(self):
        source = ': : if larger ( 5 3 ) then { print "yes" ; } else { print "no" ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["yes"])

    def test_if_false_branch(self):
        source = ': : if lesser ( 5 3 ) then { print "yes" ; } else { print "no" ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["no"])

    def test_if_eq_true(self):
        source = ': : if eq ( 5 5 ) then { print "eq" ; } else { print "neq" ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["eq"])

    def test_if_eq_false(self):
        source = ': : if eq ( 5 3 ) then { print "eq" ; } else { print "neq" ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["neq"])

    def test_not_condition(self):
        source = ': : if not ( eq ( 5 3 ) ) then { print "yes" ; } else { print "no" ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["yes"])

    def test_and_condition(self):
        source = ': : if and ( larger ( 5 3 ) larger ( 10 1 ) ) then { print "yes" ; } else { print "no" ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["yes"])

    def test_or_condition(self):
        source = ': : if or ( lesser ( 5 3 ) larger ( 10 1 ) ) then { print "yes" ; } else { print "no" ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["yes"])


class TestEvaluatorLoops(unittest.TestCase):
    """Test loop constructs."""

    def test_while_loop(self):
        source = '#c : : #c = 0 ; while lesser ( #c 3 ) do { print "x" ; #c = add ( #c 1 ) ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["x", "x", "x"])

    def test_until_loop(self):
        source = '#c : : #c = 0 ; until eq ( #c 3 ) do { print "y" ; #c = add ( #c 1 ) ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["y", "y", "y"])

    def test_do_while_loop(self):
        source = '#c : : #c = 0 ; do { print "z" ; #c = add ( #c 1 ) ; } while lesser ( #c 3 ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["z", "z", "z"])

    def test_do_until_loop(self):
        source = '#c : : #c = 0 ; do { print "w" ; #c = add ( #c 1 ) ; } until eq ( #c 3 ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["w", "w", "w"])

    def test_while_immediate_false(self):
        source = '#c : : #c = 5 ; while lesser ( #c 3 ) do { print "never" ; } ; print "done" ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["done"])


class TestEvaluatorFunctions(unittest.TestCase):
    """Test function calls."""

    def test_void_function(self):
        source = ': void #f ( ) { : : print "inside" ; return } : #f ( ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["inside"])

    def test_num_function(self):
        source = '#x : num #f ( ) { : : return ( 42 ) } : #x = #f ( ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["42"])

    def test_function_with_parameter(self):
        source = '#x : num #f ( #a ) { : : return ( add ( #a 10 ) ) } : #x = #f ( 5 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["15"])

    def test_function_with_multiple_params(self):
        source = '#x : num #add ( #a #b ) { : : return ( add ( #a #b ) ) } : #x = #add ( 3 4 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["7"])


class TestEvaluatorVariableScoping(unittest.TestCase):
    """Test variable scoping."""

    def test_variable_assignment(self):
        source = '#x : : #x = 5 ; #x = add ( #x 3 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["8"])

    def test_multiple_variables(self):
        source = '#x #y : : #x = 5 ; #y = 10 ; print ( add ( #x #y ) ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["15"])


class TestEvaluatorNopAndComment(unittest.TestCase):
    """Test nop and comment instructions."""

    def test_nop(self):
        source = ': : nop ; print "after" ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["after"])

    def test_comment(self):
        source = ': : comment "ignored" ; print "after" ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["after"])


class TestEvaluatorEmptyProgram(unittest.TestCase):
    """Test empty/minimal programs."""

    def test_empty_algorithm(self):
        source = ': : '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, [])

    def test_only_nop(self):
        source = ': : nop ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, [])


class TestEvaluatorEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def test_zero_comparison(self):
        source = ': : if eq ( 0 0 ) then { print "zero" ; } else { print "nonzero" ; } ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["zero"])

    def test_negative_number(self):
        source = '#x : : #x = -5 ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["-5"])


class TestEnvironment(unittest.TestCase):
    """Test the Environment class."""

    def test_variable_lookup(self):
        env = Environment()
        env.variables["#x"] = 42
        self.assertEqual(env.lookup_var("#x"), 42)

    def test_variable_assignment(self):
        env = Environment()
        env.assign_var("#x", 10)
        self.assertEqual(env.variables["#x"], 10)

    def test_parent_lookup(self):
        parent = Environment()
        parent.variables["#x"] = 100
        child = Environment(parent=parent)
        self.assertEqual(child.lookup_var("#x"), 100)

    def test_step_limit(self):
        env = Environment(max_steps=5)
        for _ in range(5):
            env.tick()
        with self.assertRaises(EvalError):
            env.tick()


class TestEvaluatorIntegrationAnchors(unittest.TestCase):
    """Integration tests from the spec anchors."""

    def test_div_5_2_equals_2_5(self):
        source = '#x : : #x = div ( 5 2 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["2.5"])

    def test_mod_5_2_equals_1(self):
        source = '#x : : #x = mod ( 5 2 ) ; print ( #x ) ; '
        outputs = evaluate_source(source)
        self.assertEqual(outputs, ["1"])


class TestOracleAdversarialAnchors(unittest.TestCase):
    def test_negative_remainder_truncates_toward_zero(self):
        for left, right, expected in ((-5, 2, "-1"), (5, -2, "1"), (-5, -2, "-1")):
            with self.subTest(left=left, right=right):
                self.assertEqual(evaluate_source(f": : print ( mod ( {left} {right} ) ) ; "), [expected])

    def test_float_mode_converts_integer_tokens_before_arithmetic(self):
        # IEEE binary32 cannot distinguish these neighboring large integers.
        source = ": : print ( add ( sub ( 16777217 16777216 ) 0.1 ) ) ; "
        self.assertEqual(evaluate_source(source), ["0.1"])

    def test_equality_is_exact_not_epsilon(self):
        source = ': : if eq ( 0 0.0000000001 ) then { print "bad" ; } else { print "exact" ; } ; '
        self.assertEqual(evaluate_source(source), ["exact"])

    def test_binary32_arithmetic_rounds_at_each_result(self):
        source = ': : if eq ( add ( 0.1 0.2 ) 0.3 ) then { print "yes" ; } else { print "no" ; } ; '
        self.assertEqual(evaluate_source(source), ["yes"])

    def test_binary32_cancellation_and_float_output_format(self):
        source = ': : print ( sub ( add ( 16777216 1 ) 16777216 ) ) ; print ( 0.1 ) ; print ( 100000000 ) ; '
        self.assertEqual(evaluate_source(source), ["0", "0.1", "1e+08"])

    def test_short_circuit_skips_side_effect_calls(self):
        source = '#x : num #f ( ) { : : #x = add ( #x 1 ) ; return ( #x ) } : #x = 0 ; if and ( eq ( 0 1 ) eq ( #f ( ) 1 ) ) then { nop ; } else { nop ; } ; if or ( eq ( 1 1 ) eq ( #f ( ) 1 ) ) then { nop ; } else { nop ; } ; print ( #x ) ; '
        self.assertEqual(evaluate_source(source), ["0"])

    def test_step_limit_is_shared_across_repeated_calls(self):
        source = ': void #f ( ) { : : nop ; return } : #f ( ) ; #f ( ) ; #f ( ) ; '
        with self.assertRaises(EvalError):
            evaluate_source(source, max_steps=5)

    def test_arguments_capture_left_to_right_before_later_side_effect(self):
        source = '#x : num #touch ( ) { : : #x = 9 ; return ( #x ) } num #pair ( #a #b ) { : : return ( sub ( #a #b ) ) } : #x = 3 ; print ( #pair ( #x #touch ( ) ) ) ; '
        self.assertEqual(evaluate_source(source), ["-6"])


if __name__ == "__main__":
    unittest.main()
