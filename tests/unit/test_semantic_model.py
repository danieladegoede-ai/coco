"""Identity, lookup and snapshot boundaries shared by the P2 owners."""
from dataclasses import replace
from pathlib import Path
import unittest

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.semantic_model import (
    CheckedProgram, FoundationError, NumericMode, ResolvedProgram, Scope,
    SemanticType, SourceSpan, Symbol, SymbolKind, SymbolTable,
)
from spl_frontend.source import SourceFile
from spl_frontend.tree import NodeKind, SyntaxTree


def minimal_resolved():
    tree = parse(tokenize(SourceFile(Path("sample.spl"), ": : ")), SyntaxTree())
    p = next(n for n in tree.iter_nodes() if n.contents == "P")
    table = SymbolTable()
    scope = table.add_scope(p.node_id)
    scopes = {n.node_id: scope.scope_id for n in tree.iter_nodes()}
    return ResolvedProgram(tree, table.scopes, table.symbols, scopes, {})


class SymbolTableTests(unittest.TestCase):
    def setUp(self):
        self.table = SymbolTable()
        self.root = self.table.add_scope(2)
        self.left = self.table.add_scope(20, self.root.scope_id)
        self.right = self.table.add_scope(40, self.root.scope_id)
        self.grandchild = self.table.add_scope(60, self.left.scope_id)

    def test_nearest_ancestor_wins_without_searching_siblings(self):
        outer = self.table.declare(1, SymbolKind.VARIABLE, "#x", 3)
        local = self.table.declare(2, SymbolKind.VARIABLE, "#x", 21)
        sibling_only = self.table.declare(2, SymbolKind.VARIABLE, "#private", 22)
        self.assertEqual(self.table.lookup_variable(4, "#x"), local)
        self.assertEqual(self.table.lookup_variable(3, "#x"), outer)
        self.assertIsNone(self.table.lookup_variable(3, sibling_only.original_name))
        self.assertEqual(self.left.depth, self.right.depth)
        self.assertNotEqual(self.left.scope_id, self.right.scope_id)

    def test_function_lookup_is_direct_not_ancestor_based(self):
        root_function = self.table.declare(1, SymbolKind.FUNCTION, "#f", 4)
        child_function = self.table.declare(2, SymbolKind.FUNCTION, "#g", 23)
        self.assertEqual(self.table.lookup_function(1, "#f"), root_function)
        self.assertEqual(self.table.lookup_function(2, "#g"), child_function)
        self.assertIsNone(self.table.lookup_function(2, "#f"))
        self.assertIsNone(self.table.lookup_function(3, "#g"))
        self.assertIsNone(self.table.lookup_function(1, "#g"))

    def test_parameter_and_local_share_duplicate_domain(self):
        self.table.declare(2, SymbolKind.PARAMETER, "#x", 24)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.table.declare(2, SymbolKind.VARIABLE, "#x", 25)
        self.assertEqual(len(self.table.symbols), 1)

    def test_distinct_namespaces_do_not_impose_a_language_collision_policy(self):
        variable = self.table.declare(1, SymbolKind.VARIABLE, "#same", 3)
        function = self.table.declare(1, SymbolKind.FUNCTION, "#same", 4)
        self.assertNotEqual(variable.internal_name, function.internal_name)
        self.assertEqual(self.table.lookup_variable(1, "#same"), variable)
        self.assertEqual(self.table.lookup_function(1, "#same"), function)

    def test_same_spelling_in_different_scopes_has_distinct_names(self):
        first = self.table.declare(2, SymbolKind.VARIABLE, "#x", 21)
        second = self.table.declare(3, SymbolKind.VARIABLE, "#x", 41)
        self.assertNotEqual(first.internal_name, second.internal_name)

    def test_fresh_tables_allocate_identically_without_global_state(self):
        names = []
        for _ in range(2):
            table = SymbolTable()
            table.add_scope(2)
            names.append(table.declare(1, SymbolKind.VARIABLE, "#", 3).internal_name)
        self.assertEqual(names, ["spl_v1", "spl_v1"])

    def test_duplicate_owner_root_and_unknown_parent_are_rejected(self):
        for args in [(2, 1), (80, None), (80, 99)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.table.add_scope(*args)
        self.assertEqual(len(self.table.scopes), 4)

    def test_function_signature_retains_parameter_order_and_validates_scope(self):
        function = self.table.declare(1, SymbolKind.FUNCTION, "#f", 4)
        a = self.table.declare(2, SymbolKind.PARAMETER, "#a", 25)
        b = self.table.declare(2, SymbolKind.PARAMETER, "#b", 26)
        updated = self.table.set_function_signature(function.symbol_id, 2, (b.symbol_id, a.symbol_id))
        self.assertEqual(updated.parameter_ids, (b.symbol_id, a.symbol_id))
        with self.assertRaises(ValueError):
            self.table.set_function_signature(function.symbol_id, 3, (a.symbol_id,))
        with self.assertRaises(ValueError):
            self.table.set_function_signature(function.symbol_id, 2, (a.symbol_id, a.symbol_id))
        self.assertEqual(self.table.symbols[function.symbol_id], updated)

    def test_type_update_is_validated_and_atomic(self):
        symbol = self.table.declare(1, SymbolKind.VARIABLE, "#x", 3)
        updated = self.table.set_type(symbol.symbol_id, SemanticType.NUMERIC)
        self.assertEqual(updated.value_type, SemanticType.NUMERIC)
        self.assertEqual(symbol.value_type, SemanticType.UNKNOWN)
        with self.assertRaises(ValueError):
            self.table.set_type(symbol.symbol_id, SemanticType.PROCEDURE)
        self.assertEqual(self.table.symbols[symbol.symbol_id], updated)

    def test_read_access_does_not_allow_external_table_mutation(self):
        with self.assertRaises(TypeError):
            self.table.scopes[9] = self.root
        with self.assertRaises(TypeError):
            self.table.symbols[9] = None

    def test_invalid_ids_do_not_alias_existing_integer_entries(self):
        for bad in (True, 1.0, "1", 0, -1):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.table.lookup_variable(bad, "#x")


class SnapshotTests(unittest.TestCase):
    def test_resolved_maps_are_read_only_copies(self):
        resolved = minimal_resolved()
        scopes = dict(resolved.scope_by_node)
        snapshot = replace(resolved, scope_by_node=scopes)
        scopes.clear()
        self.assertEqual(len(snapshot.scope_by_node), len(snapshot.tree))
        with self.assertRaises(TypeError):
            snapshot.scope_by_node[1] = 9

    def test_missing_or_foreign_node_scope_is_rejected(self):
        resolved = minimal_resolved()
        for changes in [{}, {**resolved.scope_by_node, 999: 1}, {**resolved.scope_by_node, 1: 999}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(resolved, scope_by_node=changes)

    def test_scope_owner_must_be_P_and_depth_must_match_parent(self):
        resolved = minimal_resolved()
        with self.assertRaises(ValueError):
            replace(resolved, scopes={1: Scope(1, None, 1, 0)})
        with self.assertRaises(ValueError):
            replace(resolved, scopes={1: Scope(1, None, 2, 0), 2: Scope(2, 1, 3, 2)})

    def test_all_name_leaves_need_matching_bindings_and_unique_internal_names(self):
        tree = parse(tokenize(SourceFile(Path("names.spl"), "#x : : #x = 1 ; ")), SyntaxTree())
        table = SymbolTable(); table.add_scope(2)
        names = [n for n in tree.iter_nodes() if n.contents == "#x"]
        symbol = table.declare(1, SymbolKind.VARIABLE, "#x", names[0].node_id)
        scopes = {n.node_id: 1 for n in tree.iter_nodes()}
        bindings = {n.node_id: symbol.symbol_id for n in names}
        resolved = ResolvedProgram(tree, table.scopes, table.symbols, scopes, bindings)
        self.assertEqual(set(resolved.renamed_name_by_node.values()), {symbol.internal_name})
        with self.assertRaises(ValueError):
            replace(resolved, binding_by_name_node={})
        with self.assertRaises(ValueError):
            replace(resolved, binding_by_name_node={n.node_id: 99 for n in names})
        self.assertTrue(all(n.contents == "#x" for n in names))

    def test_checked_boundary_requires_complete_nonterminal_annotations(self):
        resolved = minimal_resolved()
        types = {n.node_id: SemanticType.OK for n in resolved.tree.iter_nodes() if n.kind is not NodeKind.LEAF}
        checked = CheckedProgram(resolved, types, NumericMode.INTEGER)
        types.clear()
        self.assertTrue(checked.type_by_node)
        with self.assertRaises(ValueError):
            CheckedProgram(resolved, {1: SemanticType.OK}, NumericMode.INTEGER)
        with self.assertRaises(ValueError):
            CheckedProgram(resolved, {**checked.type_by_node, 1: SemanticType.UNKNOWN}, NumericMode.INTEGER)
        with self.assertRaises(ValueError):
            CheckedProgram(resolved, checked.type_by_node, "float")

    def test_span_and_xml_only_diagnostic_never_invent_original_positions(self):
        span = SourceSpan(Path("input.spl"), 3, 8, 20, 3, 10, 22)
        self.assertIn("input.spl:3:8", FoundationError("MAP", "bad", span=span).render())
        error = FoundationError("TREE-SHAPE", "bad", path=Path("tree.xml"), node_id=7)
        self.assertIn("tree.xml:node[7]", error.render())
        self.assertIsNone(error.span)
        self.assertNotIn(":1:1", error.render())

    def test_invalid_model_values_are_rejected(self):
        with self.assertRaises(ValueError): Scope(True, None, 2, 0)
        with self.assertRaises(ValueError): Scope(1, 1, 2, 1)
        with self.assertRaises(ValueError): SourceSpan(Path("x"), 1, 2, 4, 1, 1, 3)
        with self.assertRaises(ValueError): Symbol(1, SymbolKind.VARIABLE, 3, 1, "#x", "bad-name")

    def test_boolean_or_float_mapping_keys_never_alias_integer_node_ids(self):
        resolved = minimal_resolved()
        for bad in (True, 1.0):
            for field in ("scopes", "scope_by_node"):
                changed = dict(getattr(resolved, field)); changed[bad] = changed.pop(1)
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                    replace(resolved, **{field: changed})
        types = {n.node_id: SemanticType.OK for n in resolved.tree.iter_nodes() if n.kind is not NodeKind.LEAF}
        types[True] = types.pop(1)
        with self.assertRaises(ValueError): CheckedProgram(resolved, types, NumericMode.INTEGER)


if __name__ == "__main__":
    unittest.main()
