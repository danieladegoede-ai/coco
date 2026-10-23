from dataclasses import replace
from pathlib import Path
import unittest

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.semantic_model import FoundationError
from spl_frontend.source import SourceFile
from spl_frontend.source_map import SourceMap, build_source_map
from spl_frontend.tokens import Token, TokenType
from spl_frontend.tree import SyntaxTree
from spl_frontend.tree_walkers import iter_leaves


class SourceMapTests(unittest.TestCase):
    def test_repeated_names_track_exact_occurrences_under_all_line_endings(self):
        for newline in ("\n", "\r", "\r\n"):
            with self.subTest(newline=newline):
                text = f"#x : :{newline}#x = 1 ;{newline}print ( #x ) ; "
                path = Path("a folder/custom.spl")
                tokens = tokenize(SourceFile(path, text)); tree = parse(tokens, SyntaxTree(), path)
                mapping = build_source_map(tree, tokens, path)
                leaves = [n for n in iter_leaves(tree) if n.contents == "#x"]
                spans = [mapping.span_for(n.node_id) for n in leaves]
                self.assertEqual([(s.line, s.column) for s in spans], [(1, 1), (2, 1), (3, 9)])
                self.assertEqual([text[s.offset:s.end_offset] for s in spans], ["#x"] * 3)
                self.assertEqual(len({s.offset for s in spans}), 3)
                self.assertEqual(mapping.span_for(1).end_offset, tokens[-2].offset + len(tokens[-2].lexeme))
                self.assertTrue(all(s.path == path for s in spans))

    def test_mapping_uses_tree_leaf_order_not_sorted_node_ids(self):
        tree = SyntaxTree(); tree.add_root("SPL_PROG")
        tree.add_leaf("#x", 1); tree.add_leaf("#x", 1); tree.root.child_ids.reverse()
        tokens = tokenize(SourceFile(Path("x"), "#x #x "))
        mapping = build_source_map(tree, tokens, Path("x"))
        self.assertEqual(mapping.span_for(3).offset, 0)
        self.assertEqual(mapping.span_for(2).offset, 3)

    def test_nullable_nodes_have_no_fabricated_position(self):
        tokens = tokenize(SourceFile(Path("x"), ": : ")); tree = parse(tokens, SyntaxTree())
        mapping = build_source_map(tree, tokens, Path("x"))
        for node in tree.iter_nodes():
            if node.contents in {"V_DECL", "F_DECL", "ALGO"}:
                self.assertIsNone(mapping.span_for(node.node_id))
        self.assertEqual(mapping.span_for(1).offset, 0)

    def test_xml_only_empty_mapping_is_explicit(self):
        mapping = SourceMap(Path("tree.xml"), {})
        self.assertIsNone(mapping.span_for(2))

    def test_count_mismatch_and_lexeme_mismatch_are_rejected(self):
        path = Path("bad.spl")
        tokens = tokenize(SourceFile(path, ": : ")); tree = parse(tokens, SyntaxTree())
        for changed, code in [(tokens[:-2] + tokens[-1:], "MAP-COUNT"),
                              ([replace(tokens[0], lexeme=";")] + tokens[1:], "MAP-LEXEME")]:
            with self.subTest(code=code), self.assertRaises(FoundationError) as result:
                build_source_map(tree, changed, path)
            self.assertEqual(result.exception.code, code)
        self.assertIn("bad.spl:1:1", result.exception.render())
        self.assertIsNotNone(result.exception.node_id)

    def test_missing_multiple_or_early_EOF_rejected(self):
        tokens = tokenize(SourceFile(Path("x"), ": : ")); tree = parse(tokens, SyntaxTree())
        for changed in ([], tokens[:-1], tokens + tokens[-1:], [tokens[-1]] + tokens):
            with self.subTest(changed=changed), self.assertRaises(FoundationError):
                build_source_map(tree, changed, Path("x"))

    def test_overlapping_locations_or_early_EOF_are_rejected(self):
        tokens = tokenize(SourceFile(Path("x"), ": : ")); tree = parse(tokens, SyntaxTree())
        for changed in ([tokens[0], replace(tokens[1], offset=0), tokens[-1]],
                        tokens[:-1] + [replace(tokens[-1], offset=0)]):
            with self.assertRaises(FoundationError): build_source_map(tree, changed, Path("x"))

    def test_snapshot_cannot_be_mutated_through_original_mapping(self):
        tokens = tokenize(SourceFile(Path("x"), ": : ")); tree = parse(tokens, SyntaxTree())
        built = build_source_map(tree, tokens, Path("x")); values = dict(built.source_location_by_node)
        snapshot = SourceMap(Path("x"), values); values.clear()
        self.assertIsNotNone(snapshot.span_for(1))
        with self.assertRaises(TypeError): snapshot.source_location_by_node[1] = None

    def test_invalid_tree_is_wrapped_before_alignment(self):
        tree = SyntaxTree(); tree.add_root("SPL_PROG"); tree.root.child_ids.append(99)
        with self.assertRaises(FoundationError) as result:
            build_source_map(tree, [Token(TokenType.EOF, "", 1, 1, 0)], Path("x"))
        self.assertEqual(result.exception.code, "MAP-TREE")

    def test_invalid_position_values_yield_structured_alignment_errors(self):
        tokens = tokenize(SourceFile(Path("x"), ": : ")); tree = parse(tokens, SyntaxTree())
        for changed in ([replace(tokens[0], line=True)] + tokens[1:],
                        tokens[:-1] + [replace(tokens[-1], line=True)]):
            with self.assertRaises(FoundationError): build_source_map(tree, changed, Path("x"))
        with self.assertRaises(ValueError): SourceMap("x", {})


if __name__ == "__main__":
    unittest.main()
