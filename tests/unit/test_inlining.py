"""Structural freshness, actual capture and deliberate backend diagnostics."""
from dataclasses import fields
from unittest.mock import patch
import unittest

from spl_frontend.inlining import generate_program
from spl_frontend.codegen_ir import Assign, CodegenError, Comment, Label, StorageRef
from spl_frontend.tree_walkers import iter_preorder
from tests.unit.test_function_templates import checked
from spl_frontend.codegen import CodeGenerator
from spl_frontend.inlining import Inliner

def prepared(text):
    generator = CodeGenerator(checked(text))
    return generator, Inliner(generator.checked, context=generator.context)


class InliningTests(unittest.TestCase):
    def test_repeated_expansion_does_not_mutate_template_or_share_local_slots_labels(self):
        generator, inliner = prepared(
            '#x : num #f ( #p ) { #i : : #i = 0 ; '
            'while lesser ( #i #p ) do { #i = add ( #i 1 ) ; } ; '
            'return ( #i ) } : #x = #f ( 2 ) ; #x = #f ( 3 ) ; '
        )
        env = inliner.root_environment()
        template = next(iter(inliner.templates.values()))
        before = (template.declarations, template.instructions, dict(template.storage_by_symbol))
        calls = [n for n in iter_preorder(generator.checked.resolved.tree) if n.contents == "CALL"]
        destination = env.resolve(next(iter(env.storage_by_symbol)))
        first_fragment = inliner.emit_call(calls[0].node_id, destination, env, generator.context)
        second_fragment = inliner.emit_call(calls[1].node_id, destination, env, generator.context)
        first, second = first_fragment.instructions, second_fragment.instructions
        first_labels = {i.label for i in first if isinstance(i, Label)}
        second_labels = {i.label for i in second if isinstance(i, Label)}
        self.assertTrue(first_labels)
        self.assertTrue(first_labels.isdisjoint(second_labels))
        first_slots = {getattr(i, f.name) for i in first for f in fields(i)
                       if isinstance(getattr(i, f.name), StorageRef)} - {destination}
        second_slots = {getattr(i, f.name) for i in second for f in fields(i)
                        if isinstance(getattr(i, f.name), StorageRef)} - {destination}
        self.assertTrue(first_slots.isdisjoint(second_slots))
        self.assertEqual(before, (template.declarations, template.instructions, dict(template.storage_by_symbol)))
        generate_program(generator.checked).validate()

    def test_argument_operand_nodes_do_not_increase_actual_count(self):
        result = generate_program(checked(
            '#x : num #f ( #a ) { : : return ( #a ) } : '
            '#x = #f ( add ( 2 mul ( 3 4 ) ) ) ; '
        ))
        result.validate()

    def test_arity_is_generation_policy_with_real_source_location(self):
        with self.assertRaises(CodegenError) as raised:
            generate_program(checked(': void #f ( #a ) { : : return } : #f ( ) ; '))
        self.assertEqual(raised.exception.code, "GEN-ARITY")
        self.assertIsNotNone(raised.exception.span)
        self.assertIn("D04", raised.exception.message)

    def test_bounded_expansion_reports_a_deliberate_error(self):
        with patch("spl_frontend.inlining.MAX_EXPANDED_INSTRUCTIONS", 1):
            with self.assertRaises(CodegenError) as raised:
                generate_program(checked(': void #f ( ) { : : nop ; nop ; return } : #f ( ) ; '))
        self.assertEqual(raised.exception.code, "GEN-EXPANSION-LIMIT")

    def test_no_formal_or_capture_instructions_for_zero_arg_empty_procedure(self):
        result = generate_program(checked(': void #f ( ) { : : return } : #f ( ) ; '))
        self.assertTrue(all(isinstance(i, Comment) for i in result.fragment.instructions))
        self.assertEqual(result.fragment.declarations, ())
