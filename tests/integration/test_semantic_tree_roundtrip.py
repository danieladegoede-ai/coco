"""Exercise the public P2 foundation against real parser and writer output."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.semantic_model import CheckedProgram, NumericMode, ResolvedProgram, SemanticType, SymbolKind, SymbolTable
from spl_frontend.source import SourceFile
from spl_frontend.source_map import build_source_map
from spl_frontend.tree import NodeKind, SyntaxTree
from spl_frontend.tree_reader import parse_tree_xml, read_tree
from spl_frontend.tree_walkers import function_parts, iter_list_items, iter_preorder, program_parts
from spl_frontend.xml_writer import write_tree
from tools.generate_valid_spl import generate_coverage_program, generate_program


def annotated_fixture(tree: SyntaxTree, source_map) -> ResolvedProgram:
    """Explicit annotations for this known fixture; not a name-analysis pass."""
    programs = [n for n in tree.iter_nodes() if n.contents == "P"]
    table = SymbolTable()
    root_scope = table.add_scope(programs[0].node_id)
    root_parts = program_parts(tree, programs[0].node_id)
    function_node = next(iter_list_items(tree, root_parts.functions.node_id))
    function = function_parts(tree, function_node.node_id)
    child_scope = table.add_scope(function.body.node_id, root_scope.scope_id)
    formal = next(iter_list_items(tree, function.parameters.node_id))
    f = table.declare(1, SymbolKind.FUNCTION, "#f", function.name.node_id)
    a = table.declare(2, SymbolKind.PARAMETER, "#a", formal.node_id)
    table.set_function_signature(f.symbol_id, 2, (a.symbol_id,))
    scopes = {n.node_id: 1 for n in tree.iter_nodes()}
    for subtree in (function.parameters, function.body):
        scopes.update({n.node_id: 2 for n in iter_preorder(tree, subtree.node_id)})
    bindings = {n.node_id: f.symbol_id if n.contents == "#f" else a.symbol_id
                for n in tree.iter_nodes() if n.kind is NodeKind.LEAF and n.contents in {"#f", "#a"}}
    return ResolvedProgram(tree, table.scopes, table.symbols, scopes, bindings,
                           source_map.source_location_by_node)


class SemanticRoundtripTests(unittest.TestCase):
    def test_generated_parser_trees_roundtrip_with_all_list_and_function_shapes(self):
        programs = [generate_coverage_program()] + [generate_program(seed=seed) for seed in range(25)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tree.xml"
            for seed, source in enumerate(programs):
                with self.subTest(seed=seed):
                    source_path = Path("examples/generated.spl")
                    tokens = tokenize(SourceFile(source_path, source))
                    tree = parse(tokens, SyntaxTree(), source_path)
                    write_tree(tree, path); before = path.read_bytes()
                    xml = ET.fromstring(before); xml[:] = list(reversed(xml))
                    restored = parse_tree_xml(ET.tostring(xml), path)
                    self.assertEqual(list(tree.iter_nodes()), list(restored.iter_nodes()))
                    self.assertEqual(build_source_map(tree, tokens, source_path),
                                     build_source_map(restored, tokens, source_path))
                    for node in restored.iter_nodes():
                        if node.contents in {"V_DECL", "F_DECL", "INPUT", "ALGO"}:
                            list(iter_list_items(restored, node.node_id))
                        elif node.contents == "P": program_parts(restored, node.node_id)
                        elif node.contents == "F_TYPE": function_parts(restored, node.node_id)
                    write_tree(restored, path)
                    self.assertEqual(path.read_bytes(), before)

    def test_four_downstream_contract_consumers_share_one_fixture_without_mutating_P1(self):
        path = Path("a folder/fixture.spl")
        tokens = tokenize(SourceFile(path, ': void #f ( #a ) { : : print ( #a ) ; return } : #f ( 1 ) ; '))
        original = parse(tokens, SyntaxTree(), path)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "tree.xml"
            write_tree(original, output); before = output.read_bytes()
            restored = read_tree(output)
            snapshots = []
            for tree in (original, restored):
                resolved = annotated_fixture(tree, build_source_map(tree, tokens, path))
                # Name consumer: scopes and binding identities, not a spelling edit.
                self.assertEqual(len(resolved.scopes), 2)
                self.assertEqual(set(resolved.renamed_name_by_node.values()), {"spl_f1", "spl_p2"})
                # Type consumer: return a typed snapshot without mutating resolution.
                typed_symbols = {key: replace(value, value_type=SemanticType.PROCEDURE if value.kind is SymbolKind.FUNCTION else SemanticType.NUMERIC)
                                 for key, value in resolved.symbols.items()}
                typed = replace(resolved, symbols=typed_symbols)
                types = {n.node_id: SemanticType.NUMERIC if n.contents == "TERM" else SemanticType.OK
                         for n in tree.iter_nodes() if n.kind is not NodeKind.LEAF}
                types.update({node: typed.symbols[symbol].value_type for node, symbol in typed.binding_by_name_node.items()})
                checked = CheckedProgram(typed, types, NumericMode.INTEGER)
                self.assertTrue(all(s.value_type is SemanticType.UNKNOWN for s in resolved.symbols.values()))
                # Codegen consumer: IDs select names/type without importing a backend.
                self.assertEqual(checked.numeric_mode.value, "int")
                self.assertEqual(checked.resolved.renamed_name_by_node, resolved.renamed_name_by_node)
                # Inlining consumer: ordered formals and body scope survive XML.
                function = checked.resolved.symbols[1]
                self.assertEqual(function.parameter_ids, (2,))
                self.assertEqual(function.body_scope_id, 2)
                snapshots.append((dict(typed.scopes), dict(typed.symbols), dict(typed.binding_by_name_node), dict(checked.type_by_node)))
                write_tree(tree, output); self.assertEqual(output.read_bytes(), before)
            self.assertEqual(snapshots[0], snapshots[1])

    def test_invalid_resolved_signature_and_declaration_binding_are_rejected(self):
        path = Path("fixture.spl")
        tokens = tokenize(SourceFile(path, ': void #f ( #a ) { : : return } : #f ( 1 ) ; '))
        tree = parse(tokens, SyntaxTree(), path)
        resolved = annotated_fixture(tree, build_source_map(tree, tokens, path))
        with self.assertRaises(ValueError):
            replace(resolved, symbols={**resolved.symbols, 1: replace(resolved.symbols[1], body_scope_id=None)})
        with self.assertRaises(ValueError):
            replace(resolved, symbols={**resolved.symbols, 1: replace(resolved.symbols[1], parameter_ids=(99,))})
        with self.assertRaisesRegex(ValueError, "all body parameters"):
            replace(resolved, symbols={**resolved.symbols, 1: replace(resolved.symbols[1], parameter_ids=())})
        bindings = dict(resolved.binding_by_name_node)
        bindings[resolved.symbols[1].declaration_node_id] = 2
        with self.assertRaises(ValueError): replace(resolved, binding_by_name_node=bindings)

    def test_deep_tree_XML_roundtrip_avoids_python_recursion_limits(self):
        tree = SyntaxTree(); tree.add_root("SPL_PROG"); current = tree.root
        for _ in range(2200): current = tree.add_inner("P", current.node_id)
        tree.add_leaf("nop", current.node_id)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "tree.xml"
            write_tree(tree, output)
            self.assertEqual(list(read_tree(output).iter_nodes()), list(tree.iter_nodes()))


if __name__ == "__main__":
    unittest.main()
