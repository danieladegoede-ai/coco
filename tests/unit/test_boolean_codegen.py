"""Structural unit tests for the explicit Boolean destination invariant."""

import unittest

from spl_frontend.codegen import CodeGenerator, CodegenContext
from spl_frontend.codegen_ir import ConditionalJump, LabelRef
from spl_frontend.semantic_model import SemanticType
from spl_frontend.tree import NodeKind
from tests.codegen_support import checked_source


class BooleanCodegenUnitTests(unittest.TestCase):
    def _bool_node(self, checked, source_label="BOOL"):
        return next(
            node for node in checked.resolved.tree.iter_nodes()
            if node.kind is NodeKind.INNER and node.contents == source_label
        )

    def test_emit_bool_has_explicit_true_and_false_transfers(self):
        checked = checked_source(': : if eq ( 1 2 ) then { nop ; } else { nop ; } ; ')
        bool_node = self._bool_node(checked)
        self.assertIs(checked.type_by_node[bool_node.node_id], SemanticType.BOOLEAN)
        context = CodegenContext(checked)
        generator = CodeGenerator(checked, context=context)
        true_label = context.new_label()
        false_label = context.new_label()
        fragment = generator.emit_bool(bool_node.node_id, true_label, false_label)
        transfers = [item for item in fragment.instructions if isinstance(item, ConditionalJump)]
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0].true_target, true_label)
        self.assertEqual(transfers[0].false_target, false_label)

    def test_not_swaps_true_and_false_destinations(self):
        checked = checked_source(': : if not ( eq ( 1 2 ) ) then { nop ; } else { nop ; } ; ')
        # Find the outer NOT BOOL (the first BOOL preorder node).
        tree = checked.resolved.tree
        outer = next(
            node for node in tree.iter_nodes()
            if node.kind is NodeKind.INNER and node.contents == "BOOL"
            and tree.get_node(node.child_ids[0]).contents == "not"
        )
        context = CodegenContext(checked)
        generator = CodeGenerator(checked, context=context)
        true_label = context.new_label()
        false_label = context.new_label()
        fragment = generator.emit_bool(outer.node_id, true_label, false_label)
        transfer = next(item for item in fragment.instructions if isinstance(item, ConditionalJump))
        self.assertEqual(transfer.true_target, false_label)
        self.assertEqual(transfer.false_target, true_label)

    def test_and_or_include_a_rhs_entry_label_for_short_circuiting(self):
        for operator in ("and", "or"):
            with self.subTest(operator=operator):
                checked = checked_source(
                    f': : if {operator} ( eq ( 1 1 ) eq ( 2 2 ) ) '
                    'then { nop ; } else { nop ; } ; '
                )
                outer = next(
                    node for node in checked.resolved.tree.iter_nodes()
                    if node.kind is NodeKind.INNER and node.contents == "BOOL"
                    and checked.resolved.tree.get_node(node.child_ids[0]).contents == operator
                )
                context = CodegenContext(checked)
                generator = CodeGenerator(checked, context=context)
                fragment = generator.emit_bool(outer.node_id, context.new_label(), context.new_label())
                transfers = [item for item in fragment.instructions if isinstance(item, ConditionalJump)]
                self.assertEqual(len(transfers), 2)
                self.assertTrue(any(type(item).__name__ == "Label" for item in fragment.instructions))
                self.assertNotIn("&&", repr(fragment.instructions))
                self.assertNotIn("||", repr(fragment.instructions))


if __name__ == "__main__":
    unittest.main()
