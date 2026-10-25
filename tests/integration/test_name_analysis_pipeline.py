"""Public name-analysis handoff through P1 parsing, XML and semantic consumers."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from spl_frontend.lexer import tokenize
from spl_frontend.name_analysis import NameAnalysisError, build_call_hierarchy, resolve_names
from spl_frontend.parser import parse
from spl_frontend.semantic_model import CheckedProgram, NumericMode, SemanticType
from spl_frontend.source import SourceFile
from spl_frontend.source_map import build_source_map
from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode
from spl_frontend.tree_reader import read_tree
from spl_frontend.tree_walkers import iter_preorder
from spl_frontend.xml_writer import write_tree


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'semantics' / 'names'
EXAMPLE = (
    '#x : num #f ( #p #q ) { #x : '
    'num #g ( #a ) { : : return ( add ( #a #x ) ) } '
    ': #x = #p ; return ( #g ( #q ) ) } : #x = #f ( 1 2 ) ; '
)


def parse_source(text, path=Path('example.spl')):
    tokens = tokenize(SourceFile(path, text))
    tree = parse(tokens, SyntaxTree(), path)
    return tree, tokens


def semantic_snapshot(result):
    return (dict(result.scopes), dict(result.symbols), dict(result.scope_by_node),
            dict(result.binding_by_name_node), dict(result.renamed_name_by_node),
            build_call_hierarchy(result))


class NamePipelineTests(unittest.TestCase):
    def test_fixture_manifest_exercises_acceptance_and_each_name_error(self):
        cases = json.loads((FIXTURES / 'cases.json').read_text())
        self.assertEqual({case['expected'] for case in cases}, {
            'accept', 'NAME-DUPLICATE-VARIABLE', 'NAME-DUPLICATE-PARAMETER',
            'NAME-PARAMETER-MASK', 'NAME-DUPLICATE-FUNCTION',
            'NAME-UNDECLARED-VARIABLE', 'NAME-INVISIBLE-FUNCTION',
        })
        for case in cases:
            with self.subTest(fixture=case['file'], rules=case['rules']):
                path = FIXTURES / case['file']
                tree, tokens = parse_source(path.read_text(), path)
                locations = build_source_map(tree, tokens, path)
                if case['expected'] == 'accept':
                    result = resolve_names(tree, locations)
                    self.assertEqual(len(result.binding_by_name_node),
                                     sum(n.kind is NodeKind.LEAF and n.contents.startswith('#')
                                         for n in tree.iter_nodes()))
                else:
                    with self.assertRaises(NameAnalysisError) as raised:
                        resolve_names(tree, locations)
                    self.assertEqual(raised.exception.code, case['expected'])
                    self.assertEqual(raised.exception.name, case['name'])
                    self.assertEqual(raised.exception.path, path)

    def test_repeated_resolution_and_xml_roundtrip_have_identical_bindings(self):
        tree, tokens = parse_source(EXAMPLE)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'tree.xml'
            write_tree(tree, output)
            original_xml = output.read_bytes()
            snapshots = []
            for current in (tree, tree, read_tree(output)):
                result = resolve_names(current, build_source_map(current, tokens, Path('example.spl')))
                snapshots.append(semantic_snapshot(result))
                write_tree(current, output)
                self.assertEqual(output.read_bytes(), original_xml)
            self.assertEqual(snapshots[0], snapshots[1])
            self.assertEqual(snapshots[0], snapshots[2])

    def test_xml_without_tokens_resolves_same_semantics_with_empty_locations(self):
        tree, tokens = parse_source(EXAMPLE)
        original = resolve_names(tree, build_source_map(tree, tokens, Path('example.spl')))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'tree.xml'
            write_tree(tree, output)
            imported = resolve_names(read_tree(output), path=output)
        self.assertEqual(semantic_snapshot(original), semantic_snapshot(imported))
        self.assertFalse(imported.source_location_by_node)

    def test_record_and_node_number_order_do_not_control_binding(self):
        tree, tokens = parse_source(EXAMPLE)
        original = resolve_names(tree, build_source_map(tree, tokens, Path('example.spl')))
        # IDs stay sequential, but descendants can have smaller IDs than parents.
        ids = {1: 1, **{old: len(tree) + 2 - old for old in range(2, len(tree) + 1)}}
        shuffled = SyntaxTree.from_nodes(
            TreeNode(ids[n.node_id], n.kind, n.contents,
                     ids[n.parent_id] if n.parent_id is not None else None,
                     [ids[c] for c in n.child_ids])
            for n in reversed(list(tree.iter_nodes()))
        )
        changed = resolve_names(shuffled, build_source_map(shuffled, tokens, Path('example.spl')))
        self.assertEqual(
            [(s.symbol_id, s.original_name, s.internal_name, s.scope_id, s.parameter_ids)
             for s in original.symbols.values()],
            [(s.symbol_id, s.original_name, s.internal_name, s.scope_id, s.parameter_ids)
             for s in changed.symbols.values()],
        )
        self.assertEqual({ids[n]: binding for n, binding in original.binding_by_name_node.items()},
                         changed.binding_by_name_node)
        self.assertEqual([changed.scope_by_node[n.node_id] for n in iter_preorder(shuffled)],
                         [original.scope_by_node[n.node_id] for n in iter_preorder(tree)])

    def test_downstream_type_snapshot_can_consume_real_name_result(self):
        tree, tokens = parse_source(EXAMPLE)
        result = resolve_names(tree, build_source_map(tree, tokens, Path('example.spl')))
        # Explicit representation fixture, not the separate Part 2b type pass.
        typed_symbols = {i: replace(s, value_type=SemanticType.NUMERIC) for i, s in result.symbols.items()}
        typed = replace(result, symbols=typed_symbols)
        types = {n.node_id: SemanticType.OK for n in tree.iter_nodes() if n.kind is not NodeKind.LEAF}
        types.update({n: typed.symbols[s].value_type for n, s in typed.binding_by_name_node.items()})
        checked = CheckedProgram(typed, types, NumericMode.INTEGER)
        self.assertEqual(checked.resolved.binding_by_name_node, result.binding_by_name_node)
        self.assertTrue(all(s.value_type is SemanticType.UNKNOWN for s in result.symbols.values()))

    def test_inliner_fixture_gets_ordered_formals_captured_entity_and_return_call(self):
        tree, _ = parse_source(EXAMPLE)
        result = resolve_names(tree)
        f = next(s for s in result.symbols.values() if s.original_name == '#f')
        g = next(s for s in result.symbols.values() if s.original_name == '#g')
        local_x = next(s for s in result.symbols.values()
                       if s.original_name == '#x' and s.scope_id == f.body_scope_id)
        self.assertEqual([result.symbols[i].original_name for i in f.parameter_ids], ['#p', '#q'])
        captured_x = next(n for n in tree.iter_nodes() if n.kind is NodeKind.LEAF
                          and n.contents == '#x' and result.scope_by_node[n.node_id] == g.body_scope_id)
        self.assertEqual(result.binding_by_name_node[captured_x.node_id], local_x.symbol_id)
        hierarchy = build_call_hierarchy(result)
        self.assertEqual(hierarchy.callees_by_caller[f.symbol_id], (g.symbol_id,))
        self.assertLess(hierarchy.bottom_up_function_ids.index(g.symbol_id),
                        hierarchy.bottom_up_function_ids.index(f.symbol_id))


if __name__ == '__main__':
    unittest.main()
