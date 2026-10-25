from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET

from spl_frontend.semantic_model import FoundationError
from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode
from spl_frontend.tree_reader import parse_tree_xml, read_tree
from spl_frontend.xml_writer import write_tree


class TreeReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "tree.xml"
        self.tree = SyntaxTree(); self.tree.add_root("SPL_PROG")
        self.tree.add_inner("P", 1); self.tree.add_leaf(":", 2)
        write_tree(self.tree, self.path)
        self.document = self.path.read_bytes()

    def test_roundtrip_and_record_reordering_preserve_every_field(self):
        xml = ET.fromstring(self.document); xml[:] = list(reversed(xml))
        tree = parse_tree_xml(ET.tostring(xml))
        self.assertEqual(list(tree.iter_nodes()), list(self.tree.iter_nodes()))
        write_tree(tree, self.path)
        self.assertEqual(self.document, self.path.read_bytes())

    def test_import_copies_records_and_continues_allocator(self):
        nodes = [TreeNode(1, NodeKind.ROOT, "SPL_PROG", None, [3]),
                 TreeNode(2, NodeKind.LEAF, "#x", 3),
                 TreeNode(3, NodeKind.INNER, "P", 1, [2])]
        tree = SyntaxTree.from_nodes(reversed(nodes))
        nodes[0].child_ids.clear()
        self.assertEqual(tree.root.child_ids, [3])
        self.assertEqual(tree.add_leaf(";", 3).node_id, 4)
        tree.validate()

    def test_parent_ids_need_not_precede_child_ids(self):
        nodes = [TreeNode(1, NodeKind.ROOT, "SPL_PROG", None, [3]),
                 TreeNode(2, NodeKind.LEAF, "#x", 3),
                 TreeNode(3, NodeKind.INNER, "P", 1, [2])]
        tree = SyntaxTree.from_nodes(nodes); write_tree(tree, self.path)
        self.assertEqual(list(read_tree(self.path).iter_nodes()), nodes)

    def test_root_only_and_empty_children_are_supported(self):
        tree = SyntaxTree(); tree.add_root("SPL_PROG"); write_tree(tree, self.path)
        self.assertEqual(len(read_tree(self.path)), 1)

    def test_contents_are_not_stripped_or_double_decoded(self):
        tree = SyntaxTree(); tree.add_root("SPL_PROG")
        tree.add_leaf('  "a&<b>"  ', 1); write_tree(tree, self.path)
        self.assertEqual(read_tree(self.path).get_node(2).contents, '  "a&<b>"  ')

    def test_malformed_and_unsupported_documents_are_structured_errors(self):
        bad = [b"<syntax_tree>", b"<other />", b"<syntax_tree surprise='1' />",
               b"<syntax_tree>text</syntax_tree>",
               b"<syntax_tree><unknown /></syntax_tree>",
               b"<!DOCTYPE syntax_tree [<!ENTITY x 'SPL_PROG'>]><syntax_tree />"]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(FoundationError) as result:
                parse_tree_xml(data, self.path)
            self.assertEqual(result.exception.path, self.path)
            self.assertIn(result.exception.code, {"XML-PARSE", "XML-TREE"})

    def test_schema_rejects_missing_duplicate_unknown_fields_and_mixed_content(self):
        for mutation in ("missing", "duplicate", "unknown", "nested", "childtag", "tail", "attributes"):
            with self.subTest(mutation=mutation):
                xml = ET.fromstring(self.document); root = xml[0]
                if mutation == "missing": root.remove(root.find("contents"))
                elif mutation == "duplicate": ET.SubElement(root, "id").text = "1"
                elif mutation == "unknown": ET.SubElement(root, "parent").text = "9"
                elif mutation == "nested": ET.SubElement(root.find("contents"), "bad")
                elif mutation == "childtag": root.find("children")[0].tag = "bad"
                elif mutation == "tail": root.find("id").tail = "oops"
                else: root.find("id").set("hidden", "1")
                with self.assertRaises(FoundationError): parse_tree_xml(ET.tostring(xml))

    def test_graph_corruption_is_rejected(self):
        for mutation in ("duplicate-id", "dangling", "asymmetry", "cycle", "wrong-root", "orphan", "gap", "multiple-roots"):
            with self.subTest(mutation=mutation):
                xml = ET.fromstring(self.document)
                if mutation == "duplicate-id": xml[2].find("id").text = "2"
                elif mutation == "dangling": xml[0].find("children/child").text = "99"
                elif mutation == "asymmetry": xml[2].find("parent").text = "1"
                elif mutation == "cycle": ET.SubElement(xml[1].find("children"), "child").text = "1"
                elif mutation == "wrong-root": xml[0].find("contents").text = "P"
                elif mutation == "orphan": xml[0].find("children").clear()
                elif mutation == "gap": xml[2].find("id").text = "4"; xml[1].find("children/child").text = "4"
                else:
                    xml[1].tag = "root"; xml[1].remove(xml[1].find("parent")); xml[1].find("contents").text = "SPL_PROG"
                with self.assertRaises(FoundationError): parse_tree_xml(ET.tostring(xml))

    def test_positive_decimal_ids_only(self):
        for bad in ("0", "-1", "1.0", "True", "+1", "01", ""):
            with self.subTest(bad=bad):
                xml = ET.fromstring(self.document); xml[0].find("id").text = bad
                with self.assertRaises(FoundationError): parse_tree_xml(ET.tostring(xml))

    def test_missing_file_is_actionable_without_a_fake_SPL_location(self):
        missing = self.path.parent / "missing.xml"
        with self.assertRaises(FoundationError) as result: read_tree(missing)
        self.assertEqual(result.exception.code, "XML-READ")
        self.assertIn(str(missing), result.exception.render())
        self.assertIsNone(result.exception.span)

    def test_duplicate_import_records_are_not_silently_overwritten(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            SyntaxTree.from_nodes([self.tree.root, self.tree.root])

    def test_mutated_invalid_child_container_is_not_normalized_by_import(self):
        self.tree.root.child_ids = (2,)
        with self.assertRaises(ValueError): SyntaxTree.from_nodes(self.tree.iter_nodes())

    def test_UTF16_document_types_are_also_rejected(self):
        xml = '<!DOCTYPE syntax_tree [<!ENTITY x "SPL_PROG">]><syntax_tree />'
        with self.assertRaises(FoundationError): parse_tree_xml(xml.encode("utf-16"))


if __name__ == "__main__":
    unittest.main()
