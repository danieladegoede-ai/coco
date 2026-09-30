"""Unit tests for deterministic XML and safe output publication."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from spl_frontend.tree import SyntaxTree
from spl_frontend.xml_writer import write_tree


def sample_tree() -> SyntaxTree:
    tree = SyntaxTree()
    root = tree.add_root("SPL_PROG")
    program = tree.add_inner("P", root.node_id)
    tree.add_inner("V_DECL", program.node_id)
    tree.add_leaf(":", program.node_id)
    tree.add_leaf("nop", program.node_id)
    return tree


class XmlWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.output = self.directory / "tree.xml"
        self.tree = sample_tree()

    def xml_root(self) -> ET.Element:
        return ET.parse(self.output).getroot()

    def test_valid_manual_tree_is_written(self) -> None:
        write_tree(self.tree, self.output)
        self.assertTrue(self.output.is_file())
        self.assertGreater(self.output.stat().st_size, 0)

    def test_xml_declaration_uses_utf8(self) -> None:
        write_tree(self.tree, self.output)
        self.assertTrue(
            self.output.read_bytes().startswith(
                b"<?xml version='1.0' encoding='utf-8'?>\n"
            )
        )

    def test_document_root_is_syntax_tree(self) -> None:
        write_tree(self.tree, self.output)
        self.assertEqual(self.xml_root().tag, "syntax_tree")

    def test_every_node_appears_exactly_once_in_id_order(self) -> None:
        write_tree(self.tree, self.output)
        entries = list(self.xml_root())
        self.assertEqual(len(entries), len(self.tree))
        self.assertEqual([int(entry.findtext("id")) for entry in entries],
                         [1, 2, 3, 4, 5])
        self.assertEqual([entry.tag for entry in entries],
                         ["root", "inner", "inner", "leaf", "leaf"])

    def test_root_fields_are_correct(self) -> None:
        write_tree(self.tree, self.output)
        root = self.xml_root().find("root")
        self.assertIsNotNone(root)
        self.assertEqual(root.findtext("id"), "1")
        self.assertEqual(root.findtext("contents"), "SPL_PROG")
        self.assertIsNone(root.find("parent"))
        self.assertEqual([child.text for child in root.findall("children/child")],
                         ["2"])

    def test_inner_fields_are_correct(self) -> None:
        write_tree(self.tree, self.output)
        program = self.xml_root().find("inner")
        self.assertIsNotNone(program)
        self.assertEqual(program.findtext("id"), "2")
        self.assertEqual(program.findtext("contents"), "P")
        self.assertEqual(program.findtext("parent"), "1")
        self.assertEqual([child.text for child in program.findall("children/child")],
                         ["3", "4", "5"])

    def test_leaf_fields_are_correct(self) -> None:
        write_tree(self.tree, self.output)
        leaf = self.xml_root().findall("leaf")[0]
        self.assertEqual(leaf.findtext("id"), "4")
        self.assertEqual(leaf.findtext("contents"), ":")
        self.assertEqual(leaf.findtext("parent"), "2")
        self.assertIsNone(leaf.find("children"))

    def test_parent_ids_match_the_tree(self) -> None:
        write_tree(self.tree, self.output)
        for entry, node in zip(self.xml_root(), self.tree.iter_nodes()):
            with self.subTest(node_id=node.node_id):
                expected = None if node.parent_id is None else str(node.parent_id)
                self.assertEqual(entry.findtext("parent"), expected)

    def test_child_ids_preserve_tree_order(self) -> None:
        write_tree(self.tree, self.output)
        for entry, node in zip(self.xml_root(), self.tree.iter_nodes()):
            with self.subTest(node_id=node.node_id):
                self.assertEqual(
                    [int(child.text) for child in entry.findall("children/child")],
                    node.child_ids,
                )

    def test_empty_children_use_one_consistent_element(self) -> None:
        write_tree(self.tree, self.output)
        empty_inner = self.xml_root().findall("inner")[1]
        self.assertIsNotNone(empty_inner.find("children"))
        self.assertEqual(empty_inner.findall("children/child"), [])
        self.assertIn(b"<children />", self.output.read_bytes())

    def test_xml_sensitive_contents_round_trip_without_double_escaping(self) -> None:
        values = ("&", "<", ">", '"', "'", "a&b<c>d\"e'f")
        for value in values:
            with self.subTest(contents=value):
                tree = SyntaxTree()
                root = tree.add_root("SPL_PROG")
                tree.add_leaf(value, root.node_id)
                write_tree(tree, self.output)
                parsed = self.xml_root().find("leaf/contents")
                self.assertIsNotNone(parsed)
                self.assertEqual(parsed.text, value)
        data = self.output.read_bytes()
        self.assertIn(b"&amp;", data)
        self.assertIn(b"&lt;", data)
        self.assertIn(b"&gt;", data)
        self.assertNotIn(b"&amp;amp;", data)

    def test_surrounding_whitespace_in_contents_survives_indentation(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        tree.add_leaf("  token  ", root.node_id)
        write_tree(tree, self.output)
        self.assertEqual(self.xml_root().findtext("leaf/contents"), "  token  ")

    def test_unicode_contents_are_utf8_encoded(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        tree.add_leaf("café", root.node_id)
        write_tree(tree, self.output)
        self.assertIn("café".encode("utf-8"), self.output.read_bytes())
        self.assertEqual(self.xml_root().findtext("leaf/contents"), "café")

    def test_output_is_well_formed_and_indented(self) -> None:
        write_tree(self.tree, self.output)
        parsed = ET.parse(self.output)
        self.assertEqual(parsed.getroot().tag, "syntax_tree")
        data = self.output.read_bytes()
        self.assertIn(b"\n  <root>\n    <id>1</id>", data)
        self.assertTrue(data.endswith(b"</syntax_tree>\n"))
        self.assertNotIn(b"\r\n", data)

    def test_repeated_writes_of_one_tree_are_byte_identical(self) -> None:
        write_tree(self.tree, self.output)
        first = self.output.read_bytes()
        write_tree(self.tree, self.output)
        self.assertEqual(self.output.read_bytes(), first)

    def test_equivalent_separate_trees_are_byte_identical(self) -> None:
        other = self.directory / "second.xml"
        write_tree(self.tree, self.output)
        write_tree(sample_tree(), other)
        self.assertEqual(self.output.read_bytes(), other.read_bytes())

    def test_invalid_tree_is_rejected_before_creating_output(self) -> None:
        self.tree.root.child_ids.append(99)
        with self.assertRaisesRegex(ValueError, "missing child 99"):
            write_tree(self.tree, self.output)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_empty_tree_is_rejected_without_output(self) -> None:
        with self.assertRaisesRegex(ValueError, "no root"):
            write_tree(SyntaxTree(), self.output)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_root_only_structural_tree_can_be_written(self) -> None:
        # Structural validity does not mean this is a complete SPL program.
        tree = SyntaxTree()
        tree.add_root("SPL_PROG")
        write_tree(tree, self.output)
        entries = list(self.xml_root())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].findtext("contents"), "SPL_PROG")
        self.assertIsNotNone(entries[0].find("children"))

    def test_mutated_wrong_root_is_rejected_before_replacement(self) -> None:
        self.output.write_bytes(b"previous valid output")
        self.tree.root.contents = "WRONG_START"
        with self.assertRaisesRegex(ValueError, "SPL_PROG"):
            write_tree(self.tree, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous valid output")

    def test_mutated_dollar_leaf_cannot_be_published(self) -> None:
        leaf = self.tree.get_node(4)
        leaf.contents = "$"
        with self.assertRaisesRegex(ValueError, "EOF.*\\$"):
            write_tree(self.tree, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_survives_validation_failure(self) -> None:
        self.output.write_bytes(b"previous valid output")
        self.tree.root.child_ids.append(99)
        with self.assertRaises(ValueError):
            write_tree(self.tree, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous valid output")
        self.assertEqual(set(self.directory.iterdir()), {self.output})

    def test_serialization_failure_preserves_output_and_removes_temp(self) -> None:
        self.output.write_bytes(b"previous valid output")

        def fail_after_partial_write(_document, file, **_kwargs) -> None:
            file.write(b"<partial")
            raise OSError("simulated serialization failure")

        with patch("spl_frontend.xml_writer.ET.ElementTree.write",
                   autospec=True, side_effect=fail_after_partial_write):
            with self.assertRaisesRegex(OSError, "simulated serialization failure"):
                write_tree(self.tree, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous valid output")
        self.assertEqual(set(self.directory.iterdir()), {self.output})

    def test_temporary_file_creation_failure_preserves_output(self) -> None:
        self.output.write_bytes(b"previous valid output")
        with patch("spl_frontend.xml_writer.tempfile.NamedTemporaryFile",
                   side_effect=OSError("simulated temporary creation failure")):
            with self.assertRaisesRegex(OSError, "temporary creation failure"):
                write_tree(self.tree, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous valid output")
        self.assertEqual(set(self.directory.iterdir()), {self.output})

    def test_os_buffer_flush_failure_preserves_output_and_removes_temp(self) -> None:
        self.output.write_bytes(b"previous valid output")
        with patch("spl_frontend.xml_writer.os.fsync",
                   side_effect=OSError("simulated fsync failure")):
            with self.assertRaisesRegex(OSError, "simulated fsync failure"):
                write_tree(self.tree, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous valid output")
        self.assertEqual(set(self.directory.iterdir()), {self.output})

    def test_existing_regular_output_is_replaced_atomically(self) -> None:
        self.output.write_bytes(b"previous valid output")
        write_tree(self.tree, self.output)
        self.assertEqual(self.xml_root().tag, "syntax_tree")
        self.assertNotEqual(self.output.read_bytes(), b"previous valid output")
        self.assertEqual(set(self.directory.iterdir()), {self.output})

    def test_replace_failure_preserves_output_and_removes_temp(self) -> None:
        self.output.write_bytes(b"previous valid output")
        temporary_names: list[Path] = []

        def fail_replace(source, destination) -> None:
            temporary_names.append(Path(source))
            self.assertEqual(Path(source).parent, Path(destination).parent)
            raise OSError("simulated replacement failure")

        with patch("spl_frontend.xml_writer.os.replace", side_effect=fail_replace):
            with self.assertRaisesRegex(OSError, "simulated replacement failure"):
                write_tree(self.tree, self.output)
        self.assertEqual(len(temporary_names), 1)
        self.assertFalse(temporary_names[0].exists())
        self.assertEqual(self.output.read_bytes(), b"previous valid output")
        self.assertEqual(set(self.directory.iterdir()), {self.output})

    def test_xml_verification_failure_removes_temp_and_preserves_output(self) -> None:
        self.output.write_bytes(b"previous valid output")
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        tree.add_leaf("bad\x00character", root.node_id)
        # ElementTree versions may reject illegal XML during writing or parsing.
        with self.assertRaises((ValueError, ET.ParseError)):
            write_tree(tree, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous valid output")
        self.assertEqual(set(self.directory.iterdir()), {self.output})

    def test_normalized_contents_are_not_published(self) -> None:
        self.output.write_bytes(b"previous valid output")
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        tree.add_leaf("line\rbreak", root.node_id)
        with self.assertRaisesRegex(ValueError, "contents cannot be preserved exactly"):
            write_tree(tree, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous valid output")
        self.assertEqual(set(self.directory.iterdir()), {self.output})

    def test_missing_parent_directory_is_rejected(self) -> None:
        missing = self.directory / "missing" / "tree.xml"
        with self.assertRaisesRegex(FileNotFoundError, "parent directory does not exist"):
            write_tree(self.tree, missing)
        self.assertFalse(missing.parent.exists())

    def test_file_as_parent_directory_is_rejected(self) -> None:
        parent_file = self.directory / "file"
        parent_file.write_text("not a directory", encoding="utf-8")
        with self.assertRaisesRegex(NotADirectoryError, "not a directory"):
            write_tree(self.tree, parent_file / "tree.xml")

    def test_directory_destination_is_rejected(self) -> None:
        directory_output = self.directory / "tree.xml"
        directory_output.mkdir()
        with self.assertRaisesRegex(IsADirectoryError, "destination is a directory"):
            write_tree(self.tree, directory_output)

    def test_string_and_path_destinations_both_work(self) -> None:
        string_output = self.directory / "string.xml"
        write_tree(self.tree, str(string_output))
        write_tree(self.tree, self.output)
        self.assertEqual(string_output.read_bytes(), self.output.read_bytes())

    def test_destination_symlink_is_rejected(self) -> None:
        target = self.directory / "target.xml"
        target.write_bytes(b"previous valid output")
        self.output.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "not a regular file"):
            write_tree(self.tree, self.output)
        self.assertEqual(target.read_bytes(), b"previous valid output")


if __name__ == "__main__":
    unittest.main()
