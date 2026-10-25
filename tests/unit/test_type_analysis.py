"""Tests for the type analysis module."""

import unittest
from pathlib import Path

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.name_analysis import resolve_names
from spl_frontend.semantic_model import NumericMode, SemanticType
from spl_frontend.type_analysis import check_types, TypeAnalysisError


def make_checked(source: str):
    """Parse, resolve names, and check types for SPL source string."""
    sf = SourceFile(path=Path("test.spl"), text=source)
    tokens = tokenize(sf)
    tree = SyntaxTree()
    parse(tokens, tree, Path("test.spl"))
    tree.validate()
    resolved = resolve_names(tree, path=Path("test.spl"))
    return check_types(resolved)


class TestTypeAnalysisBasicValid(unittest.TestCase):
    """Test basic valid type scenarios."""

    def test_empty_program(self):
        source = ": : "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)
        root = checked.resolved.tree.root
        self.assertEqual(checked.type_by_node[root.node_id], SemanticType.OK)

    def test_simple_assignment(self):
        source = "#x : : #x = 5 ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_print_string(self):
        source = ': : print "hello" ; '
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_print_numeric(self):
        source = "#x : : #x = 5 ; print ( #x ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_nop_instruction(self):
        source = ": : nop ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_comment_instruction(self):
        source = ': : comment "test" ; '
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)


class TestTypeAnalysisArithmetic(unittest.TestCase):
    """Test arithmetic operations."""

    def test_add(self):
        source = "#x : : #x = add ( 5 3 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_sub(self):
        source = "#x : : #x = sub ( 5 3 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_mul(self):
        source = "#x : : #x = mul ( 5 3 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_div(self):
        source = "#x : : #x = div ( 5 3 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.FLOAT)

    def test_mod(self):
        source = "#x : : #x = mod ( 5 3 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_neg(self):
        source = "#x : : #x = neg ( 5 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_nested_arithmetic(self):
        source = "#x : : #x = add ( sub ( 5 2 ) mul ( 3 4 ) ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)


class TestTypeAnalysisBooleans(unittest.TestCase):
    """Test boolean operations."""

    def test_eq(self):
        source = "#x : : if eq ( 5 5 ) then { nop ; } else { nop ; } ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_larger(self):
        source = "#x : : if larger ( 5 3 ) then { nop ; } else { nop ; } ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_lesser(self):
        source = "#x : : if lesser ( 3 5 ) then { nop ; } else { nop ; } ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_not(self):
        source = "#x : : if not ( eq ( 5 5 ) ) then { nop ; } else { nop ; } ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_and(self):
        source = "#x : : if and ( eq ( 5 5 ) larger ( 5 3 ) ) then { nop ; } else { nop ; } ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_or(self):
        source = "#x : : if or ( eq ( 5 5 ) larger ( 5 3 ) ) then { nop ; } else { nop ; } ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)


class TestTypeAnalysisLoops(unittest.TestCase):
    """Test loop constructs."""

    def test_while_loop(self):
        source = "#x : : #x = 0 ; while eq ( #x 5 ) do { #x = add ( #x 1 ) ; } ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_until_loop(self):
        source = "#x : : #x = 0 ; until eq ( #x 5 ) do { #x = add ( #x 1 ) ; } ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_do_while_loop(self):
        source = "#x : : #x = 0 ; do { #x = add ( #x 1 ) ; } while eq ( #x 5 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_do_until_loop(self):
        source = "#x : : #x = 0 ; do { #x = add ( #x 1 ) ; } until eq ( #x 5 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)


class TestTypeAnalysisFunctions(unittest.TestCase):
    """Test function declarations and calls."""

    def test_void_function_as_instruction(self):
        source = ": void #f ( ) { : : return } : #f ( ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_num_function_in_term(self):
        source = "#x : num #f ( ) { : : return ( 5 ) } : #x = #f ( ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_num_function_in_print(self):
        source = ": num #f ( ) { : : return ( 5 ) } : print ( #f ( ) ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_function_with_parameters(self):
        source = "#x : num #f ( #a ) { : : return ( #a ) } : #x = #f ( 5 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_function_with_multiple_parameters(self):
        source = "#x : num #f ( #a #b ) { : : return ( add ( #a #b ) ) } : #x = #f ( 5 3 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)


class TestTypeAnalysisInvalidCases(unittest.TestCase):
    """Test invalid type scenarios."""

    def test_num_function_as_instruction_fails(self):
        source = ": num #f ( ) { : : return ( 1 ) } : #f ( ) ; "
        with self.assertRaises(TypeAnalysisError) as ctx:
            make_checked(source)
        self.assertEqual(ctx.exception.code, "TYPE-INSTR-CALL")

    def test_void_function_in_term_fails(self):
        source = "#x : void #f ( ) { : : return } : #x = #f ( ) ; "
        with self.assertRaises(TypeAnalysisError) as ctx:
            make_checked(source)
        self.assertEqual(ctx.exception.code, "TYPE-TERM-CALL")

    def test_void_function_in_print_fails(self):
        source = ": void #f ( ) { : : return } : print ( #f ( ) ) ; "
        with self.assertRaises(TypeAnalysisError) as ctx:
            make_checked(source)
        self.assertEqual(ctx.exception.code, "TYPE-TERM-CALL")


class TestTypeAnalysisNumericConflicts(unittest.TestCase):
    """Test numeric policy conflicts are caught."""

    def test_mod_div_conflict(self):
        source = "#x : : #x = add ( mod ( 5 2 ) div ( 4 2 ) ) ; "
        with self.assertRaises(TypeAnalysisError) as ctx:
            make_checked(source)
        self.assertEqual(ctx.exception.code, "FLOAT-INT-CONFLICT")

    def test_mod_decimal_conflict(self):
        source = "#x : : #x = mod ( 5 2.1 ) ; "
        with self.assertRaises(TypeAnalysisError) as ctx:
            make_checked(source)
        self.assertEqual(ctx.exception.code, "DECIMAL-WITH-MOD")


class TestTypeAnalysisUncalledBodies(unittest.TestCase):
    """Test that uncalled function bodies are still type-checked."""

    def test_uncalled_function_with_valid_body(self):
        source = ": num #f ( ) { : : return ( 5 ) } : nop ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)

    def test_uncalled_function_numeric_conflict_detected(self):
        source = "#x : num #f ( ) { : : return ( div ( 5 2 ) ) } : #x = mod ( 5 2 ) ; "
        with self.assertRaises(TypeAnalysisError) as ctx:
            make_checked(source)
        self.assertEqual(ctx.exception.code, "FLOAT-INT-CONFLICT")


class TestTypeAnalysisNestedFunctions(unittest.TestCase):
    """Test nested function scenarios."""

    def test_nested_function_call(self):
        source = "#x : num #f ( ) { : num #g ( ) { : : return ( 5 ) } : return ( #g ( ) ) } : #x = #f ( ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.INTEGER)


class TestTypeAnalysisDecimalMode(unittest.TestCase):
    """Test decimal/float mode scenarios."""

    def test_decimal_literal_sets_float_mode(self):
        source = "#x : : #x = 3.14 ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.FLOAT)

    def test_negative_decimal_sets_float_mode(self):
        source = "#x : : #x = -3.14 ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.FLOAT)

    def test_div_sets_float_mode(self):
        source = "#x : : #x = div ( 5 2 ) ; "
        checked = make_checked(source)
        self.assertEqual(checked.numeric_mode, NumericMode.FLOAT)


class TestTypeAnalysisSymbolTypes(unittest.TestCase):
    """Test that symbol types are correctly assigned."""

    def test_variable_type_is_numeric(self):
        source = "#x : : #x = 5 ; "
        checked = make_checked(source)
        for symbol in checked.resolved.symbols.values():
            if symbol.original_name == "#x":
                self.assertEqual(symbol.value_type, SemanticType.NUMERIC)

    def test_void_function_type_is_procedure(self):
        source = ": void #f ( ) { : : return } : #f ( ) ; "
        checked = make_checked(source)
        for symbol in checked.resolved.symbols.values():
            if symbol.original_name == "#f":
                self.assertEqual(symbol.value_type, SemanticType.PROCEDURE)

    def test_num_function_type_is_numeric(self):
        source = "#x : num #f ( ) { : : return ( 5 ) } : #x = #f ( ) ; "
        checked = make_checked(source)
        for symbol in checked.resolved.symbols.values():
            if symbol.original_name == "#f":
                self.assertEqual(symbol.value_type, SemanticType.NUMERIC)


class TestTypeSnapshotsAndLocations(unittest.TestCase):
    def test_check_is_repeatable_and_does_not_mutate_resolved_tree_or_symbols(self):
        source = '#x : num #f ( #p ) { : : return ( add ( #p 1 ) ) } : #x = #f ( 2 ) ; '
        path = Path("stable.spl")
        tree = SyntaxTree()
        parse(tokenize(SourceFile(path, source)), tree, path)
        resolved = resolve_names(tree, path=path)
        original_symbols = dict(resolved.symbols)
        snapshot = lambda: [(n.node_id, n.kind, n.contents, n.parent_id, tuple(n.child_ids)) for n in tree.iter_nodes()]
        original_tree = snapshot()
        checked1, checked2 = check_types(resolved), check_types(resolved)
        self.assertEqual(dict(resolved.symbols), original_symbols)
        self.assertEqual(snapshot(), original_tree)
        self.assertEqual(dict(checked1.type_by_node), dict(checked2.type_by_node))
        for node in tree.iter_nodes():
            if node.child_ids or node.contents in ("V_DECL", "F_DECL", "ALGO", "INPUT"):
                self.assertNotEqual(checked1.type_by_node[node.node_id], SemanticType.UNKNOWN)

    def test_numeric_conflict_keeps_real_source_location(self):
        from spl_frontend.source_map import build_source_map
        path = Path("located.spl")
        source = '#x : :\n#x = add ( mod ( 5 2 ) div ( 4 2 ) ) ; '
        tokens = tokenize(SourceFile(path, source)); tree = SyntaxTree()
        parse(tokens, tree, path)
        resolved = resolve_names(tree, source_map=build_source_map(tree, tokens, path))
        with self.assertRaises(TypeAnalysisError) as caught:
            check_types(resolved)
        self.assertEqual(caught.exception.span.line, 2)
        self.assertIn("located.spl:2:", caught.exception.render())

    def test_arity_not_invented_as_part2b_type_error(self):
        # No matching-count rule is supplied in Part2b. The backend separately
        # documents its argument binding policy for executable programs.
        checked = make_checked(': num #f ( #p ) { : : return ( #p ) } : print ( #f ( ) ) ; ')
        self.assertEqual(checked.type_by_node[checked.resolved.tree.root.node_id], SemanticType.OK)


if __name__ == "__main__":
    unittest.main()
