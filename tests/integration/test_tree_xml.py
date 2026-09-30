"""Round-trip tests for manually built syntax trees and their XML output."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from spl_frontend.tree import NodeKind, SyntaxTree
from spl_frontend.xml_writer import write_tree


def minimal_tree() -> SyntaxTree:
    tree = SyntaxTree()
    root = tree.add_root("SPL_PROG")
    tree.add_inner("P", root.node_id)
    return tree


def declarations_tree() -> SyntaxTree:
    tree = minimal_tree()
    program = tree.get_node(2)
    declarations = tree.add_inner("V_DECL", program.node_id)
    tree.add_leaf("#count", declarations.node_id)
    tree.add_inner("V_DECL", declarations.node_id)
    tree.add_leaf(":", program.node_id)
    tree.add_inner("F_DECL", program.node_id)
    tree.add_leaf(":", program.node_id)
    tree.add_inner("ALGO", program.node_id)
    return tree


def function_tree() -> SyntaxTree:
    tree = minimal_tree()
    program = tree.get_node(2)
    functions = tree.add_inner("F_DECL", program.node_id)
    function = tree.add_inner("F_TYPE", functions.node_id)
    tree.add_leaf("num", function.node_id)
    tree.add_leaf("#square", function.node_id)
    tree.add_leaf("(", function.node_id)
    arguments = tree.add_inner("V_DECL", function.node_id)
    tree.add_leaf("#x", arguments.node_id)
    tree.add_leaf(")", function.node_id)
    tree.add_leaf("{", function.node_id)
    tree.add_inner("P", function.node_id)
    tree.add_leaf("return", function.node_id)
    tree.add_leaf("(", function.node_id)
    term = tree.add_inner("TERM", function.node_id)
    tree.add_leaf("#x", term.node_id)
    tree.add_leaf(")", function.node_id)
    tree.add_leaf("}", function.node_id)
    tree.add_inner("F_DECL", functions.node_id)
    return tree


def branch_tree() -> SyntaxTree:
    tree = minimal_tree()
    program = tree.get_node(2)
    algorithm = tree.add_inner("ALGO", program.node_id)
    instruction = tree.add_inner("INSTR", algorithm.node_id)
    branch = tree.add_inner("BRANCH", instruction.node_id)
    tree.add_leaf("if", branch.node_id)
    condition = tree.add_inner("BOOL", branch.node_id)
    tree.add_leaf("eq", condition.node_id)
    left = tree.add_inner("TERM", condition.node_id)
    tree.add_leaf("#x", left.node_id)
    right = tree.add_inner("TERM", condition.node_id)
    tree.add_leaf("0", right.node_id)
    tree.add_leaf("then", branch.node_id)
    tree.add_leaf("{", branch.node_id)
    then_algorithm = tree.add_inner("ALGO", branch.node_id)
    then_instruction = tree.add_inner("INSTR", then_algorithm.node_id)
    tree.add_leaf("nop", then_instruction.node_id)
    tree.add_leaf("}", branch.node_id)
    tree.add_leaf("else", branch.node_id)
    tree.add_leaf("{", branch.node_id)
    tree.add_inner("ALGO", branch.node_id)
    tree.add_leaf("}", branch.node_id)
    return tree


def nested_tree() -> SyntaxTree:
    tree = declarations_tree()
    program = tree.get_node(2)
    algorithm = tree.get_node(program.child_ids[-1])
    instruction = tree.add_inner("INSTR", algorithm.node_id)
    loop = tree.add_inner("LOOP", instruction.node_id)
    condition_keyword = tree.add_inner("COND", loop.node_id)
    tree.add_leaf("while", condition_keyword.node_id)
    boolean = tree.add_inner("BOOL", loop.node_id)
    tree.add_leaf("lesser", boolean.node_id)
    left = tree.add_inner("TERM", boolean.node_id)
    tree.add_leaf("#count", left.node_id)
    right = tree.add_inner("TERM", boolean.node_id)
    tree.add_leaf("10", right.node_id)
    tree.add_leaf("do", loop.node_id)
    tree.add_leaf("{", loop.node_id)
    body = tree.add_inner("ALGO", loop.node_id)
    body_instruction = tree.add_inner("INSTR", body.node_id)
    branch = tree.add_inner("BRANCH", body_instruction.node_id)
    tree.add_leaf("if", branch.node_id)
    test = tree.add_inner("BOOL", branch.node_id)
    tree.add_leaf("not", test.node_id)
    nested_test = tree.add_inner("BOOL", test.node_id)
    tree.add_leaf("eq", nested_test.node_id)
    tree.add_leaf("then", branch.node_id)
    tree.add_inner("ALGO", branch.node_id)
    tree.add_leaf("else", branch.node_id)
    tree.add_inner("ALGO", branch.node_id)
    tree.add_leaf("}", loop.node_id)
    return tree


class TreeXmlIntegrationTests(unittest.TestCase):
    def assert_round_trip(self, tree: SyntaxTree) -> None:
        tree.validate()
        before = tuple(
            (node.node_id, node.kind, node.contents, node.parent_id,
             tuple(node.child_ids))
            for node in tree.iter_nodes()
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "tree.xml"
            write_tree(tree, output)
            first_bytes = output.read_bytes()
            self.assertNotIn(b"<contents>$</contents>", first_bytes)
            document = ET.parse(output)
            self.assertEqual(document.getroot().tag, "syntax_tree")
            entries = list(document.getroot())
            self.assertEqual(len(entries), len(tree))
            self.assertEqual([int(entry.findtext("id")) for entry in entries],
                             [node.node_id for node in tree.iter_nodes()])
            for entry, node in zip(entries, tree.iter_nodes()):
                with self.subTest(node_id=node.node_id):
                    self.assertEqual(entry.tag, node.kind.value)
                    self.assertEqual(entry.findtext("contents"), node.contents)
                    expected_parent = (
                        None if node.parent_id is None else str(node.parent_id)
                    )
                    self.assertEqual(entry.findtext("parent"), expected_parent)
                    children = entry.find("children")
                    if node.kind is NodeKind.LEAF:
                        self.assertIsNone(children)
                    else:
                        self.assertIsNotNone(children)
                        self.assertEqual(
                            [int(child.text) for child in children.findall("child")],
                            node.child_ids,
                        )
            write_tree(tree, output)
            self.assertEqual(output.read_bytes(), first_bytes)
            self.assertEqual(set(Path(directory).iterdir()), {output})
        self.assertEqual(
            tuple((node.node_id, node.kind, node.contents, node.parent_id,
                   tuple(node.child_ids)) for node in tree.iter_nodes()),
            before,
        )

    def test_minimal_spl_prog_and_p(self) -> None:
        self.assert_round_trip(minimal_tree())

    def test_variable_declarations_and_terminal_leaves(self) -> None:
        self.assert_round_trip(declarations_tree())

    def test_representative_function_subtree(self) -> None:
        self.assert_round_trip(function_tree())

    def test_branch_subtree(self) -> None:
        self.assert_round_trip(branch_tree())

    def test_larger_nested_tree(self) -> None:
        self.assert_round_trip(nested_tree())

    def test_wide_tree_keeps_all_children_in_order(self) -> None:
        tree = minimal_tree()
        program = tree.get_node(2)
        for number in range(300):
            tree.add_leaf(str(number), program.node_id)
        self.assert_round_trip(tree)

    def test_deep_tree_serializes_without_recursion_failure(self) -> None:
        tree = minimal_tree()
        parent = tree.get_node(2)
        for _ in range(2500):
            parent = tree.add_inner("P", parent.node_id)
        tree.add_leaf("nop", parent.node_id)
        self.assert_round_trip(tree)


if __name__ == "__main__":
    unittest.main()
