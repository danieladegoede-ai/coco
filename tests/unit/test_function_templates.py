"""Code mines are real bottom-up immutable structural IR, not reparsed text."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import unittest

from spl_frontend.codegen import CodeGenerator, generate_target
from spl_frontend.codegen_ir import CodegenError, PrintString
from spl_frontend.function_templates import prepare_function_templates
from spl_frontend.lexer import tokenize
from spl_frontend.name_analysis import resolve_names
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.source_map import build_source_map
from spl_frontend.tree import SyntaxTree
from spl_frontend.type_analysis import check_types


def checked(text):
    path = Path("templates.spl")
    tokens = tokenize(SourceFile(path, text))
    tree = parse(tokens, SyntaxTree(), path)
    return check_types(resolve_names(tree, build_source_map(tree, tokens, path)))


def prepared(text):
    generator = CodeGenerator(checked(text))
    return generator, prepare_function_templates(generator.checked, context=generator.context)


class FunctionTemplateTests(unittest.TestCase):
    def test_zero_one_multiple_formals_return_shapes_and_own_locals(self):
        generator, inliner = prepared(
            ': void #z ( ) { : : nop ; return } '
            'num #one ( #p ) { #local : : #local = #p ; return ( #local ) } '
            'num #many ( #a #b #c ) { : : return ( add ( #a add ( #b #c ) ) ) } : '
        )
        templates = list(inliner.templates.values())
        self.assertEqual([len(t.formal_symbol_ids) for t in templates], [0, 1, 3])
        self.assertIsNone(templates[0].return_storage)
        self.assertIsNotNone(templates[1].return_storage)
        self.assertEqual(len(templates[1].local_symbol_ids), 1)
        self.assertEqual(generate_target(generator.checked).fragment.instructions, ())
        self.assertEqual(generate_target(generator.checked).fragment.declarations, ())
        self.assertTrue(inliner.code_mine)

    def test_all_lexical_children_precede_parent_including_uncalled(self):
        _, inliner = prepared(
            ': void #parent ( ) { : void #child ( ) { : '
            'void #grandchild ( ) { : : return } : return } : return } : '
        )
        names = [inliner.checked.resolved.symbols[i].original_name for i in inliner.preparation_order]
        self.assertEqual(names, ["#grandchild", "#child", "#parent"])
        parent = inliner.templates[inliner.preparation_order[-1]]
        self.assertEqual(parent.child_function_ids, (inliner.preparation_order[1],))

    def test_free_capture_uses_declaration_identity_and_keeps_outer_names_distinct(self):
        _, inliner = prepared(
            '#x : void #parent ( ) { #x : void #child ( ) { : : '
            '#x = add ( #x 1 ) ; return } : #x = 4 ; #child ( ) ; return } : '
        )
        child = next(t for i, t in inliner.templates.items() if inliner.checked.resolved.symbols[i].original_name == "#child")
        parent = next(t for i, t in inliner.templates.items() if inliner.checked.resolved.symbols[i].original_name == "#parent")
        self.assertEqual(child.captured_symbol_ids, parent.local_symbol_ids)
        self.assertEqual(parent.captured_symbol_ids, ())
        self.assertTrue(set(child.capture_storage_by_symbol.values()).isdisjoint(child.declarations))

    def test_children_are_expanded_inside_parent_code_mine(self):
        _, inliner = prepared(
            ': void #parent ( ) { : void #child ( ) { : : print "child" ; return } '
            ': #child ( ) ; return } : '
        )
        parent = next(t for i, t in inliner.templates.items() if inliner.checked.resolved.symbols[i].original_name == "#parent")
        self.assertTrue(any(isinstance(i, PrintString) and i.value.value == "child" for i in parent.instructions))

    def test_snapshot_maps_and_instruction_sequences_cannot_be_mutated(self):
        _, inliner = prepared(': num #f ( #x ) { : : return ( #x ) } : ')
        template = next(iter(inliner.templates.values()))
        with self.assertRaises(TypeError):
            template.storage_by_symbol[8] = None
        with self.assertRaises(FrozenInstanceError):
            template.instructions = ()
        with self.assertRaises(TypeError):
            inliner.templates[8] = template

    def test_forged_recursive_binding_is_a_deliberate_generation_error(self):
        program = checked(': void #f ( ) { : void #f ( ) { : : return } : #f ( ) ; return } : ')
        functions = [s for s in program.resolved.symbols.values() if s.original_name == '#f']
        call = next(n for n in program.resolved.tree.iter_nodes() if n.contents == 'CALL')
        bindings = dict(program.resolved.binding_by_name_node)
        bindings[call.child_ids[0]] = functions[0].symbol_id
        forged = replace(program, resolved=replace(program.resolved, binding_by_name_node=bindings))
        with self.assertRaises(CodegenError) as caught:
            prepare_function_templates(forged)
        self.assertEqual(caught.exception.code, 'GEN-TEMPLATE-HIERARCHY')

    def test_malformed_procedure_return_metadata_is_rejected(self):
        _, result = prepared(': void #f ( ) { : : return } : ')
        template = next(iter(result.templates.values()))
        from spl_frontend.codegen_ir import StorageRef
        with self.assertRaises(ValueError):
            replace(template, return_storage=StorageRef(1))

    def test_template_expansion_budget_reports_structured_failure(self):
        from unittest.mock import patch
        with patch('spl_frontend.function_templates.MAX_EXPANDED_INSTRUCTIONS', 1):
            with self.assertRaises(CodegenError) as caught:
                prepare_function_templates(checked(': void #f ( ) { : : nop ; nop ; return } : '))
        self.assertEqual(caught.exception.code, 'GEN-EXPANSION-LIMIT')
