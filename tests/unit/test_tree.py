"""Builder and corruption tests for the concrete syntax tree."""

from __future__ import annotations

import unittest

from spl_frontend.tree import NodeKind, SyntaxTree, TreeBuilder, TreeNode


def snapshot(tree: SyntaxTree) -> tuple[tuple[object, ...], ...]:
    """Capture public node data to check that rejection/validation is read-only."""
    return tuple(
        (n.node_id, n.kind, n.contents, n.parent_id, tuple(n.child_ids))
        for n in tree.iter_nodes()
    )


class SyntaxTreeBuilderTests(unittest.TestCase):
    def test_fresh_tree_has_no_root_or_nodes(self) -> None:
        tree = SyntaxTree()
        self.assertIsNone(tree.root)
        self.assertEqual(len(tree), 0)

    def test_first_root_has_id_one_and_correct_fields(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        self.assertEqual(root.node_id, 1)
        self.assertIs(root.kind, NodeKind.ROOT)
        self.assertEqual(root.contents, "SPL_PROG")
        self.assertIsNone(root.parent_id)
        self.assertEqual(root.child_ids, [])
        self.assertIs(tree.root, root)

    def test_inner_and_leaf_have_sequential_ids_and_correct_fields(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        inner = tree.add_inner("P", root.node_id)
        leaf = tree.add_leaf(":", inner.node_id)
        self.assertEqual([root.node_id, inner.node_id, leaf.node_id], [1, 2, 3])
        self.assertEqual((inner.kind, inner.contents, inner.parent_id),
                         (NodeKind.INNER, "P", root.node_id))
        self.assertEqual((leaf.kind, leaf.contents, leaf.parent_id),
                         (NodeKind.LEAF, ":", inner.node_id))
        self.assertEqual(inner.child_ids, [leaf.node_id])
        self.assertEqual(leaf.child_ids, [])

    def test_two_fresh_trees_assign_the_same_ids(self) -> None:
        def build() -> list[int]:
            tree = SyntaxTree()
            root = tree.add_root("SPL_PROG")
            inner = tree.add_inner("P", root.node_id)
            leaf = tree.add_leaf("nop", inner.node_id)
            return [root.node_id, inner.node_id, leaf.node_id]

        self.assertEqual(build(), build())

    def test_children_keep_insertion_order_and_parent_links(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        first = tree.add_inner("P", root.node_id)
        second = tree.add_leaf(":", root.node_id)
        third = tree.add_inner("F_DECL", root.node_id)
        self.assertEqual(root.child_ids, [first.node_id, second.node_id, third.node_id])
        self.assertEqual([n.parent_id for n in (first, second, third)], [1, 1, 1])

    def test_second_root_is_rejected_without_change(self) -> None:
        tree = SyntaxTree()
        tree.add_root("SPL_PROG")
        before = snapshot(tree)
        with self.assertRaisesRegex(ValueError, "only one root"):
            tree.add_root("ANOTHER")
        self.assertEqual(snapshot(tree), before)
        self.assertEqual(tree.add_leaf("nop", 1).node_id, 2)

    def test_root_must_be_start_symbol_without_consuming_an_id(self) -> None:
        tree = SyntaxTree()
        with self.assertRaisesRegex(ValueError, "SPL_PROG"):
            tree.add_root("WRONG_START")
        self.assertEqual(len(tree), 0)
        self.assertEqual(tree.add_root("SPL_PROG").node_id, 1)

    def test_missing_parent_is_rejected_without_change(self) -> None:
        tree = SyntaxTree()
        tree.add_root("SPL_PROG")
        before = snapshot(tree)
        for method in (tree.add_inner, tree.add_leaf):
            with self.subTest(method=method.__name__):
                with self.assertRaisesRegex(ValueError, "Parent ID 99 does not exist"):
                    method("P", 99)
                self.assertEqual(snapshot(tree), before)
        self.assertEqual(tree.add_inner("P", 1).node_id, 2)

    def test_leaf_cannot_be_parent_and_rejection_does_not_consume_id(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        leaf = tree.add_leaf("nop", root.node_id)
        before = snapshot(tree)
        for method in (tree.add_inner, tree.add_leaf):
            with self.subTest(method=method.__name__):
                with self.assertRaisesRegex(ValueError, "Leaf node 2 cannot have children"):
                    method("P", leaf.node_id)
                self.assertEqual(snapshot(tree), before)
        self.assertEqual(tree.add_leaf(":", root.node_id).node_id, 3)

    def test_empty_and_non_string_contents_are_rejected_atomically(self) -> None:
        tree = SyntaxTree()
        for bad in ("", "   ", "\t", None, 0, []):
            with self.subTest(method="add_root", contents=bad):
                with self.assertRaisesRegex(ValueError, "non-empty string"):
                    tree.add_root(bad)  # type: ignore[arg-type]
                self.assertEqual(len(tree), 0)
        root = tree.add_root("SPL_PROG")
        before = snapshot(tree)
        for method in (tree.add_inner, tree.add_leaf):
            for bad in ("", "   ", "\t", None, 0, []):
                with self.subTest(method=method.__name__, contents=bad):
                    with self.assertRaisesRegex(ValueError, "non-empty string"):
                        method(bad, root.node_id)  # type: ignore[arg-type]
                    self.assertEqual(snapshot(tree), before)
        self.assertEqual(tree.add_inner("P", root.node_id).node_id, 2)

    def test_parent_ids_must_be_exact_positive_integers(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        before = snapshot(tree)
        for method in (tree.add_inner, tree.add_leaf):
            for bad in (None, True, False, 1.0, 0.0, "1", 0, -1, []):
                with self.subTest(method=method.__name__, parent_id=bad):
                    with self.assertRaisesRegex(ValueError, "positive integer"):
                        method("P", bad)  # type: ignore[arg-type]
                    self.assertEqual(snapshot(tree), before)
        self.assertEqual(tree.add_inner("P", root.node_id).node_id, 2)

    def test_dollar_is_not_a_leaf_and_rejection_keeps_the_id(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        with self.assertRaisesRegex(ValueError, "EOF.*\\$"):
            tree.add_leaf("$", root.node_id)
        self.assertEqual(root.child_ids, [])
        self.assertEqual(tree.add_leaf(":", root.node_id).node_id, 2)

    def test_get_node_returns_managed_node_and_unknown_id_is_clear(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        self.assertIs(tree.get_node(root.node_id), root)
        with self.assertRaisesRegex(ValueError, "Node ID 99 does not exist"):
            tree.get_node(99)

    def test_get_node_rejects_invalid_id_types_and_values(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        for bad in (None, True, False, 1.0, "1", 0, -1, []):
            with self.subTest(node_id=bad):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    tree.get_node(bad)  # type: ignore[arg-type]
        self.assertIs(tree.get_node(1), root)

    def test_iteration_and_length_are_deterministic(self) -> None:
        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        tree.add_leaf(":", root.node_id)
        tree.add_inner("P", root.node_id)
        self.assertEqual([node.node_id for node in tree.iter_nodes()], [1, 2, 3])
        self.assertEqual(len(tree), 3)
        self.assertEqual([node.node_id for node in tree.iter_nodes()], [1, 2, 3])

    def test_implements_tree_builder_protocol(self) -> None:
        builder: TreeBuilder = SyntaxTree()
        root = builder.add_root("SPL_PROG")
        builder.add_leaf("nop", root.node_id)
        builder.validate()


class SyntaxTreeValidationTests(unittest.TestCase):
    """Direct private-state edits model corruption public builder calls prevent."""

    def setUp(self) -> None:
        self.tree = SyntaxTree()
        self.root = self.tree.add_root("SPL_PROG")

    def test_valid_manually_built_tree_passes(self) -> None:
        program = self.tree.add_inner("P", self.root.node_id)
        self.tree.add_inner("V_DECL", program.node_id)
        self.tree.add_leaf(":", program.node_id)
        self.tree.validate()

    def test_validation_does_not_change_valid_tree(self) -> None:
        program = self.tree.add_inner("P", self.root.node_id)
        self.tree.add_leaf("nop", program.node_id)
        before = snapshot(self.tree)
        self.tree.validate()
        self.assertEqual(snapshot(self.tree), before)
        self.assertEqual(self.tree.add_leaf(":", program.node_id).node_id, 4)

    def test_root_only_tree_is_valid(self) -> None:
        # This is structurally valid, not a complete SPL program.
        self.tree.validate()

    def test_empty_tree_has_no_root(self) -> None:
        with self.assertRaisesRegex(ValueError, "no root"):
            SyntaxTree().validate()

    def test_stored_nodes_with_no_root_are_rejected(self) -> None:
        self.tree._nodes[1].kind = NodeKind.INNER
        with self.assertRaisesRegex(ValueError, "no root"):
            self.tree.validate()

    def test_multiple_roots_are_rejected(self) -> None:
        self.tree._nodes[2] = TreeNode(2, NodeKind.ROOT, "SPL_PROG", None)
        with self.assertRaisesRegex(ValueError, "2 root nodes"):
            self.tree.validate()

    def test_root_with_parent_is_rejected(self) -> None:
        self.root.parent_id = 2
        with self.assertRaisesRegex(ValueError, "Root node 1 cannot have a parent"):
            self.tree.validate()

    def test_wrong_start_symbol_is_rejected_after_mutation(self) -> None:
        self.root.contents = "WRONG_START"
        with self.assertRaisesRegex(ValueError, "SPL_PROG"):
            self.tree.validate()

    def test_dollar_leaf_is_rejected_after_mutation(self) -> None:
        leaf = self.tree.add_leaf(":", self.root.node_id)
        leaf.contents = "$"
        with self.assertRaisesRegex(ValueError, "EOF.*\\$"):
            self.tree.validate()

    def test_non_root_without_parent_is_rejected(self) -> None:
        child = self.tree.add_inner("P", 1)
        child.parent_id = None
        with self.assertRaisesRegex(ValueError, "Non-root node 2 has no parent"):
            self.tree.validate()

    def test_non_root_with_missing_parent_is_rejected(self) -> None:
        child = self.tree.add_inner("P", 1)
        child.parent_id = 99
        with self.assertRaisesRegex(ValueError, "Node 2 refers to missing parent 99"):
            self.tree.validate()

    def test_parent_with_missing_child_is_rejected(self) -> None:
        self.root.child_ids.append(99)
        with self.assertRaisesRegex(ValueError, "Parent 1 lists missing child 99"):
            self.tree.validate()

    def test_child_back_pointer_to_another_parent_is_rejected(self) -> None:
        first = self.tree.add_inner("P", 1)
        second = self.tree.add_inner("F_DECL", 1)
        child = self.tree.add_leaf(":", first.node_id)
        child.parent_id = second.node_id
        with self.assertRaisesRegex(ValueError, "Child 4 is listed under parent 2 but points to parent 3"):
            self.tree.validate()

    def test_child_missing_from_its_parent_list_is_rejected(self) -> None:
        self.tree.add_inner("P", 1)
        self.root.child_ids.clear()
        with self.assertRaisesRegex(ValueError, "Node 2 is missing from parent 1's child IDs"):
            self.tree.validate()

    def test_duplicate_child_under_one_parent_is_rejected(self) -> None:
        child = self.tree.add_leaf("nop", 1)
        self.root.child_ids.append(child.node_id)
        with self.assertRaisesRegex(ValueError, "Parent 1 lists child 2 twice"):
            self.tree.validate()

    def test_child_listed_under_two_parents_is_rejected(self) -> None:
        first = self.tree.add_inner("P", 1)
        second = self.tree.add_inner("F_DECL", 1)
        child = self.tree.add_leaf(":", first.node_id)
        second.child_ids.append(child.node_id)
        with self.assertRaisesRegex(ValueError, "Child 4 is listed under both parents 2 and 3"):
            self.tree.validate()

    def test_leaf_with_children_is_rejected(self) -> None:
        leaf = self.tree.add_leaf("nop", 1)
        leaf.child_ids.append(1)
        with self.assertRaisesRegex(ValueError, "Leaf node 2 has children"):
            self.tree.validate()

    def test_cycle_is_rejected(self) -> None:
        child = self.tree.add_inner("P", 1)
        child.child_ids.append(1)
        with self.assertRaisesRegex(ValueError, "Cycle detected through parent 2 and child 1"):
            self.tree.validate()

    def test_self_cycle_is_rejected(self) -> None:
        self.root.child_ids.append(self.root.node_id)
        with self.assertRaisesRegex(ValueError, "Cycle detected"):
            self.tree.validate()

    def test_three_node_cycle_is_rejected(self) -> None:
        self.tree._nodes[2] = TreeNode(2, NodeKind.INNER, "P", 4, [3])
        self.tree._nodes[3] = TreeNode(3, NodeKind.INNER, "V_DECL", 2, [4])
        self.tree._nodes[4] = TreeNode(4, NodeKind.INNER, "F_DECL", 3, [2])
        with self.assertRaisesRegex(ValueError, "Cycle detected"):
            self.tree.validate()

    def test_cycle_in_disconnected_component_is_rejected(self) -> None:
        # This locally consistent component cannot be reached from the root.
        self.tree._nodes[2] = TreeNode(2, NodeKind.INNER, "P", 3, [3])
        self.tree._nodes[3] = TreeNode(3, NodeKind.INNER, "V_DECL", 2, [2])
        with self.assertRaisesRegex(ValueError, "Cycle detected"):
            self.tree.validate()

    def test_unreachable_node_is_reported(self) -> None:
        # A finite detached component also violates a parent-link rule or cycles.
        child = self.tree.add_inner("P", 1)
        self.root.child_ids.clear()
        with self.assertRaisesRegex(ValueError, "Node 2 is unreachable from root 1"):
            self.tree.validate()
        self.assertEqual(child.parent_id, 1)

    def test_unreachable_component_is_reported(self) -> None:
        first = self.tree.add_inner("P", 1)
        self.tree.add_inner("V_DECL", first.node_id)
        self.root.child_ids.clear()
        with self.assertRaisesRegex(ValueError, "unreachable from root 1"):
            self.tree.validate()

    def test_mapping_key_different_from_node_id_is_rejected(self) -> None:
        child = self.tree.add_inner("P", 1)
        del self.tree._nodes[child.node_id]
        self.tree._nodes[3] = child
        with self.assertRaisesRegex(ValueError, "mapping key 3 differs from node ID 2"):
            self.tree.validate()

    def test_boolean_mapping_key_is_rejected(self) -> None:
        self.tree._nodes = {True: self.root}
        with self.assertRaisesRegex(ValueError, "mapping key.*invalid"):
            self.tree.validate()

    def test_other_invalid_mapping_key_types_and_values_are_rejected(self) -> None:
        for bad in (1.0, "1", 0, -1, None):
            with self.subTest(mapping_key=bad):
                self.tree._nodes = {bad: self.root}
                with self.assertRaisesRegex(ValueError, "mapping key.*invalid"):
                    self.tree.validate()
        self.tree._nodes = {1: self.root}

    def test_duplicate_node_ids_are_rejected(self) -> None:
        self.tree._nodes[2] = TreeNode(2, NodeKind.INNER, "P", 1)
        self.tree._nodes[3] = TreeNode(2, NodeKind.INNER, "V_DECL", 1)
        with self.assertRaisesRegex(ValueError, "Duplicate node ID 2"):
            self.tree.validate()

    def test_gap_in_node_ids_is_rejected(self) -> None:
        child = self.tree.add_inner("P", 1)
        leaf = self.tree.add_leaf(":", child.node_id)
        del self.tree._nodes[leaf.node_id]
        leaf.node_id = 4
        self.tree._nodes[4] = leaf
        child.child_ids[:] = [4]
        with self.assertRaisesRegex(ValueError, "sequential.*starting at 1"):
            self.tree.validate()

    def test_root_must_have_first_node_id_after_corruption(self) -> None:
        child = self.tree.add_inner("P", 1)
        self.tree._nodes = {1: child, 2: self.root}
        child.node_id = 1
        child.parent_id = 2
        self.root.node_id = 2
        self.root.child_ids[:] = [1]
        with self.assertRaisesRegex(ValueError, "Root node ID must be 1"):
            self.tree.validate()

    def test_root_listed_as_child_is_rejected(self) -> None:
        child = self.tree.add_inner("P", 1)
        child.child_ids.append(self.root.node_id)
        with self.assertRaisesRegex(ValueError, "Cycle detected"):
            self.tree.validate()

    def test_invalid_contents_are_rejected(self) -> None:
        for bad in ("", "  ", None, 0):
            with self.subTest(contents=bad):
                self.root.contents = bad  # type: ignore[assignment]
                with self.assertRaisesRegex(ValueError, "Node 1 has invalid contents"):
                    self.tree.validate()

    def test_invalid_node_kind_is_rejected(self) -> None:
        self.root.kind = "branch"  # type: ignore[assignment]
        with self.assertRaisesRegex(ValueError, "Node 1 has invalid kind"):
            self.tree.validate()

    def test_invalid_node_id_is_rejected(self) -> None:
        self.root.node_id = 0
        with self.assertRaisesRegex(ValueError, "invalid ID"):
            self.tree.validate()

    def test_mutated_node_id_types_are_rejected(self) -> None:
        for bad in (None, True, False, 1.0, "1", []):
            with self.subTest(node_id=bad):
                self.root.node_id = bad  # type: ignore[assignment]
                with self.assertRaisesRegex(ValueError, "invalid ID"):
                    self.tree.validate()
                self.root.node_id = 1

    def test_invalid_parent_id_is_rejected(self) -> None:
        child = self.tree.add_inner("P", 1)
        child.parent_id = "1"  # type: ignore[assignment]
        with self.assertRaisesRegex(ValueError, "Node 2 has invalid parent ID"):
            self.tree.validate()

    def test_mutated_parent_id_types_are_rejected(self) -> None:
        child = self.tree.add_inner("P", 1)
        for bad in (True, False, 1.0, 0, -1, []):
            with self.subTest(parent_id=bad):
                child.parent_id = bad  # type: ignore[assignment]
                with self.assertRaisesRegex(ValueError, "invalid parent ID"):
                    self.tree.validate()
                child.parent_id = 1

    def test_invalid_child_id_is_rejected(self) -> None:
        self.root.child_ids.append(0)
        with self.assertRaisesRegex(ValueError, "Parent 1 has invalid child ID"):
            self.tree.validate()

    def test_mutated_child_id_types_are_rejected(self) -> None:
        for bad in (None, True, False, 1.0, "2", -1, []):
            with self.subTest(child_id=bad):
                self.root.child_ids.append(bad)  # type: ignore[arg-type]
                with self.assertRaisesRegex(ValueError, "invalid child ID"):
                    self.tree.validate()
                self.root.child_ids.pop()

    def test_invalid_child_collection_is_rejected(self) -> None:
        self.root.child_ids = None  # type: ignore[assignment]
        with self.assertRaisesRegex(ValueError, "Node 1 has invalid child IDs"):
            self.tree.validate()

    def test_validation_does_not_change_an_invalid_tree(self) -> None:
        child = self.tree.add_leaf(":", self.root.node_id)
        child.contents = "$"
        before = snapshot(self.tree)
        with self.assertRaises(ValueError):
            self.tree.validate()
        self.assertEqual(snapshot(self.tree), before)

    def test_non_root_cannot_have_a_leaf_parent(self) -> None:
        leaf = self.tree.add_leaf("nop", 1)
        child = self.tree.add_inner("P", 1)
        self.root.child_ids.remove(child.node_id)
        leaf.child_ids.append(child.node_id)
        child.parent_id = leaf.node_id
        with self.assertRaisesRegex(ValueError, "Leaf node 2 has children"):
            self.tree.validate()

    def test_deep_valid_tree_avoids_recursion_limit(self) -> None:
        parent = self.root
        for _ in range(2500):
            parent = self.tree.add_inner("P", parent.node_id)
        self.tree.add_leaf("nop", parent.node_id)
        self.tree.validate()
        self.assertEqual(len(self.tree), 2502)


class TreeNodeConstructionTests(unittest.TestCase):
    def test_ids_must_be_exact_positive_integers(self) -> None:
        for bad in (None, True, False, 1.0, 0.0, "1", 0, -1, []):
            with self.subTest(node_id=bad):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    TreeNode(bad, NodeKind.ROOT, "SPL_PROG", None)  # type: ignore[arg-type]

    def test_invalid_kinds_are_rejected(self) -> None:
        for bad in ("root", "branch", None, 1):
            with self.subTest(kind=bad):
                with self.assertRaisesRegex(ValueError, "node kind"):
                    TreeNode(1, bad, "SPL_PROG", None)  # type: ignore[arg-type]

    def test_contents_must_be_nonempty_nonwhitespace_strings(self) -> None:
        for bad in ("", "   ", "\t", None, 0):
            with self.subTest(contents=bad):
                with self.assertRaisesRegex(ValueError, "non-empty string"):
                    TreeNode(1, NodeKind.ROOT, bad, None)  # type: ignore[arg-type]

    def test_root_requires_start_symbol_and_no_parent(self) -> None:
        with self.assertRaisesRegex(ValueError, "SPL_PROG"):
            TreeNode(1, NodeKind.ROOT, "WRONG_START", None)
        with self.assertRaisesRegex(ValueError, "root.*parent"):
            TreeNode(1, NodeKind.ROOT, "SPL_PROG", 2)

    def test_nonroot_parent_must_be_exact_positive_integer(self) -> None:
        for bad in (None, True, False, 1.0, "1", 0, -1, []):
            with self.subTest(parent_id=bad):
                with self.assertRaisesRegex(ValueError, "parent ID"):
                    TreeNode(2, NodeKind.INNER, "P", bad)  # type: ignore[arg-type]

    def test_child_collection_must_be_a_list(self) -> None:
        for bad in (None, (2,), "2"):
            with self.subTest(child_ids=bad):
                with self.assertRaisesRegex(ValueError, "child IDs"):
                    TreeNode(1, NodeKind.ROOT, "SPL_PROG", None, bad)  # type: ignore[arg-type]

    def test_child_ids_must_be_exact_positive_integers(self) -> None:
        for bad in (None, True, False, 1.0, "1", 0, -1, []):
            with self.subTest(child_id=bad):
                with self.assertRaisesRegex(ValueError, "child ID"):
                    TreeNode(1, NodeKind.ROOT, "SPL_PROG", None, [bad])  # type: ignore[list-item]

    def test_direct_dollar_leaf_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "EOF.*\\$"):
            TreeNode(2, NodeKind.LEAF, "$", 1)


if __name__ == "__main__":
    unittest.main()
