from pathlib import Path
import unittest

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.semantic_model import FoundationError
from spl_frontend.source import SourceFile
from spl_frontend.tree import NodeKind, SyntaxTree
from spl_frontend.tree_walkers import function_parts, iter_leaves, iter_list_items, iter_postorder, iter_preorder, program_parts


def parsed(source):
    return parse(tokenize(SourceFile(Path("fixture.spl"), source)), SyntaxTree())


class TreeWalkerTests(unittest.TestCase):
    def test_every_recursive_list_kind_preserves_just_its_own_items(self):
        tree = parsed('#a #b : void #f ( #p #q ) { : : return } num #g ( ) { : : return ( 1 ) } : #f ( add ( 1 2 ) 3 ) ; nop ; ')
        program = next(n for n in tree.iter_nodes() if n.contents == "P")
        parts = program_parts(tree, program.node_id)
        self.assertEqual([n.contents for n in iter_list_items(tree, parts.variables.node_id)], ["#a", "#b"])
        funcs = list(iter_list_items(tree, parts.functions.node_id))
        self.assertEqual([function_parts(tree, f.node_id).name.contents for f in funcs], ["#f", "#g"])
        self.assertEqual(len(list(iter_list_items(tree, parts.algorithm.node_id))), 2)
        inputs = next(n for n in tree.iter_nodes() if n.contents == "INPUT")
        self.assertEqual(len(list(iter_list_items(tree, inputs.node_id))), 2)
        self.assertEqual(function_parts(tree, funcs[0].node_id).return_term, None)
        self.assertEqual(function_parts(tree, funcs[1].node_id).return_term.contents, "TERM")

    def test_all_nullable_lists_yield_no_items(self):
        tree = parsed(": void #f ( ) { : : return } : #f ( ) ; ")
        for node in tree.iter_nodes():
            if node.contents in {"V_DECL", "F_DECL", "INPUT", "ALGO"} and not node.child_ids:
                self.assertEqual(list(iter_list_items(tree, node.node_id)), [])

    def test_traversal_order_follows_child_edges_not_node_ids(self):
        tree = SyntaxTree(); tree.add_root("SPL_PROG")
        first = tree.add_leaf("#a", 1); second = tree.add_leaf("#b", 1)
        tree.root.child_ids.reverse()
        self.assertEqual([n.node_id for n in iter_leaves(tree)], [second.node_id, first.node_id])
        self.assertEqual([n.node_id for n in iter_postorder(tree)], [3, 2, 1])
        self.assertEqual([n.node_id for n in iter_preorder(tree)], [1, 3, 2])

    def test_deep_lists_and_traversals_are_iterative(self):
        tree = SyntaxTree(); tree.add_root("SPL_PROG")
        current = tree.add_inner("V_DECL", 1); first = current.node_id
        for _ in range(4000):
            tree.add_leaf("#x", current.node_id)
            current = tree.add_inner("V_DECL", current.node_id)
        tree.validate()
        self.assertEqual(len(list(iter_list_items(tree, first))), 4000)
        self.assertEqual(len(list(iter_preorder(tree))), len(tree))
        self.assertEqual(len(list(iter_postorder(tree))), len(tree))

    def test_local_shape_errors_are_explicit(self):
        tree = parsed(": : nop ; ")
        algorithm = next(n for n in tree.iter_nodes() if n.contents == "ALGO")
        separator = tree.get_node(algorithm.child_ids[1]); separator.contents = ":"
        with self.assertRaises(FoundationError) as result:
            list(iter_list_items(tree, algorithm.node_id))
        self.assertEqual(result.exception.code, "TREE-SHAPE")
        with self.assertRaises(FoundationError): list(iter_list_items(tree, 1))
        with self.assertRaises(FoundationError): program_parts(tree, 1)

    def test_cycle_and_missing_link_do_not_hang_walkers(self):
        tree = SyntaxTree(); tree.add_root("SPL_PROG")
        child = tree.add_inner("ALGO", 1)
        child.child_ids.append(1)
        for walker in (iter_preorder, iter_postorder):
            with self.assertRaises(FoundationError): list(walker(tree))
        child.child_ids[:] = [999]
        with self.assertRaises(FoundationError): list(iter_leaves(tree))

    def test_wrong_function_shape_rejected(self):
        tree = parsed(": num #f ( ) { : : return ( 1 ) } : ")
        function = next(n for n in tree.iter_nodes() if n.contents == "F_TYPE")
        tree.get_node(function.child_ids[-1]).contents = ")"
        with self.assertRaises(FoundationError): function_parts(tree, function.node_id)


if __name__ == "__main__":
    unittest.main()
