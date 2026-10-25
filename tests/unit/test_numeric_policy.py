"""Tests for the whole-program numeric policy scanner."""

import unittest
from pathlib import Path

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.semantic_model import NumericMode
from spl_frontend.numeric_policy import (
    scan_numeric_policy,
    NumericPolicyError,
    NumericScanResult,
)


def make_tree(source: str) -> SyntaxTree:
    """Parse SPL source string into a syntax tree for testing."""
    sf = SourceFile(path=Path("test.spl"), text=source)
    tokens = tokenize(sf)
    tree = SyntaxTree()
    parse(tokens, tree, Path("test.spl"))
    tree.validate()
    return tree


class TestNumericPolicyBasicCases(unittest.TestCase):
    """Test basic numeric policy detection."""

    def test_neither_operator_returns_integer_mode(self):
        source = "#x : : #x = 5 ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_mod)
        self.assertFalse(result.has_div)
        self.assertFalse(result.has_decimal)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_only_mod_returns_integer_mode(self):
        source = "#x : : #x = mod ( 5 2 ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertTrue(result.has_mod)
        self.assertFalse(result.has_div)
        self.assertFalse(result.has_decimal)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_only_div_returns_float_mode(self):
        source = "#x : : #x = div ( 5 2 ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_mod)
        self.assertTrue(result.has_div)
        self.assertFalse(result.has_decimal)
        self.assertEqual(result.mode, NumericMode.FLOAT)

    def test_decimal_without_operator_returns_float_mode(self):
        source = "#x : : #x = 3.14 ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_mod)
        self.assertFalse(result.has_div)
        self.assertTrue(result.has_decimal)
        self.assertEqual(result.mode, NumericMode.FLOAT)

    def test_negative_decimal_returns_float_mode(self):
        source = "#x : : #x = -3.14 ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertTrue(result.has_decimal)
        self.assertEqual(result.mode, NumericMode.FLOAT)


class TestNumericPolicyConflicts(unittest.TestCase):
    """Test numeric policy conflict detection."""

    def test_mod_and_div_conflict_exact_message(self):
        source = "#x : : #x = add ( mod ( 5 2 ) div ( 4 2 ) ) ; "
        tree = make_tree(source)
        with self.assertRaises(NumericPolicyError) as ctx:
            scan_numeric_policy(tree)
        self.assertEqual(ctx.exception.code, "FLOAT-INT-CONFLICT")
        self.assertEqual(
            ctx.exception.message,
            "A float-integer-conflict might perhaps be possible"
        )

    def test_mod_with_decimal_conflict(self):
        source = "#x : : #x = mod ( 5 2.1 ) ; "
        tree = make_tree(source)
        with self.assertRaises(NumericPolicyError) as ctx:
            scan_numeric_policy(tree)
        self.assertEqual(ctx.exception.code, "DECIMAL-WITH-MOD")


class TestNumericPolicyStringAndComments(unittest.TestCase):
    """Test that strings and comments don't trigger conflicts."""

    def test_mod_in_string_not_detected(self):
        source = ': : print "mod" ; '
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_mod)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_div_in_string_not_detected(self):
        source = ': : print "div" ; '
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_div)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_dot_in_string_not_detected_as_decimal(self):
        source = ': : print "3.14" ; '
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_decimal)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_mod_in_comment_not_detected(self):
        source = ': : comment "mod" ; '
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_mod)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_real_mod_with_string_mod_text(self):
        source = '#x : : #x = mod ( 5 2 ) ; print "mod" ; '
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertTrue(result.has_mod)
        self.assertEqual(result.mode, NumericMode.INTEGER)


class TestNumericPolicyAcrossFunctions(unittest.TestCase):
    """Test numeric policy detection across function boundaries."""

    def test_mod_in_uncalled_function_detected(self):
        source = ': num #f ( ) { : : return ( mod ( 5 2 ) ) } : nop ; '
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertTrue(result.has_mod)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_div_in_uncalled_function_detected(self):
        source = ': num #f ( ) { : : return ( div ( 5 2 ) ) } : nop ; '
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertTrue(result.has_div)
        self.assertEqual(result.mode, NumericMode.FLOAT)

    def test_mod_in_main_div_in_uncalled_function_conflict(self):
        source = '#x : num #f ( ) { : : return ( div ( 5 2 ) ) } : #x = mod ( 5 2 ) ; '
        tree = make_tree(source)
        with self.assertRaises(NumericPolicyError) as ctx:
            scan_numeric_policy(tree)
        self.assertEqual(ctx.exception.code, "FLOAT-INT-CONFLICT")

    def test_decimal_in_uncalled_function_with_mod_in_main_conflict(self):
        source = '#x : num #f ( ) { : : return ( 2.5 ) } : #x = mod ( 5 2 ) ; '
        tree = make_tree(source)
        with self.assertRaises(NumericPolicyError) as ctx:
            scan_numeric_policy(tree)
        self.assertEqual(ctx.exception.code, "DECIMAL-WITH-MOD")


class TestNumericPolicyEmptyCases(unittest.TestCase):
    """Test empty or minimal programs."""

    def test_empty_algorithm(self):
        source = ": : "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_mod)
        self.assertFalse(result.has_div)
        self.assertFalse(result.has_decimal)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_only_print_string(self):
        source = ': : print "hello" ; '
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_only_nop(self):
        source = ": : nop ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertEqual(result.mode, NumericMode.INTEGER)


class TestNumericPolicyArithmetic(unittest.TestCase):
    """Test various arithmetic operations."""

    def test_add_sub_mul_no_conflict(self):
        source = "#x : : #x = add ( sub ( 5 2 ) mul ( 3 4 ) ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertFalse(result.has_mod)
        self.assertFalse(result.has_div)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_neg_no_conflict(self):
        source = "#x : : #x = neg ( 5 ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertEqual(result.mode, NumericMode.INTEGER)

    def test_multiple_mod_detected_once(self):
        source = "#x : : #x = add ( mod ( 5 2 ) mod ( 3 4 ) ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertTrue(result.has_mod)
        self.assertIsNotNone(result.mod_node_id)

    def test_multiple_div_detected_once(self):
        source = "#x : : #x = add ( div ( 5 2 ) div ( 3 4 ) ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertTrue(result.has_div)
        self.assertIsNotNone(result.div_node_id)


class TestNumericPolicyIntegrationAnchors(unittest.TestCase):
    """Integration anchor tests from the spec."""

    def test_anchor_div_5_2_float_mode(self):
        source = "#x : : #x = div ( 5 2 ) ; print ( #x ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertEqual(result.mode, NumericMode.FLOAT)

    def test_anchor_mod_5_2_int_mode(self):
        source = "#x : : #x = mod ( 5 2 ) ; print ( #x ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        self.assertEqual(result.mode, NumericMode.INTEGER)


class TestNumericScanResultImmutability(unittest.TestCase):
    """Test that scan results are immutable."""

    def test_result_is_frozen(self):
        source = "#x : : #x = mod ( 5 2 ) ; "
        tree = make_tree(source)
        result = scan_numeric_policy(tree)
        with self.assertRaises(AttributeError):
            result.has_mod = False


class TestRepeatedScans(unittest.TestCase):
    """Test that repeated scans don't leak state."""

    def test_scan_different_trees_independently(self):
        source1 = "#x : : #x = mod ( 5 2 ) ; "
        source2 = "#x : : #x = div ( 5 2 ) ; "
        tree1 = make_tree(source1)
        tree2 = make_tree(source2)
        result1 = scan_numeric_policy(tree1)
        result2 = scan_numeric_policy(tree2)
        self.assertTrue(result1.has_mod)
        self.assertFalse(result1.has_div)
        self.assertFalse(result2.has_mod)
        self.assertTrue(result2.has_div)

    def test_rescan_same_tree_same_result(self):
        source = "#x : : #x = mod ( 5 2 ) ; "
        tree = make_tree(source)
        result1 = scan_numeric_policy(tree)
        result2 = scan_numeric_policy(tree)
        self.assertEqual(result1.has_mod, result2.has_mod)
        self.assertEqual(result1.mode, result2.mode)


if __name__ == "__main__":
    unittest.main()
