"""Compile-and-run coverage for arithmetic, assignments, and simple instructions."""

import unittest
from pathlib import Path

from spl_frontend.codegen import CodeGenerator, CodegenContext, generate_target
from spl_frontend.codegen_ir import (
    Assign,
    CodegenError,
    Comment,
    IRFragment,
    NumberLiteral,
    PrintNumber,
    StorageKind,
    StringLiteral,
    SymbolRef,
    TargetProgram,
)
from spl_frontend.semantic_model import NumericMode
from spl_frontend.target_writer import render_target
from spl_frontend.tree import NodeKind
from spl_frontend.tree_walkers import function_parts, iter_list_items, program_parts
from tests.codegen_support import TARGET_CXX, checked_source, compile_and_run_target, run_source


@unittest.skipUnless(TARGET_CXX, "a C++ compiler is required for executable codegen tests")
class ArithmeticCodegenTests(unittest.TestCase):
    def test_add_subtract_and_multiply(self):
        run_source(
            ": : print ( add ( 2 3 ) ) ; print ( sub ( 8 3 ) ) ; print ( mul ( 2 3 ) ) ; ",
            "556",
        )

    def test_division_of_integer_looking_literals_is_fractional(self):
        generated = run_source(": : print ( div ( 5 2 ) ) ; ", "2.5")
        self.assertIn("float", generated)
        self.assertIn("5.0", generated)
        self.assertIn("2.0", generated)

    def test_modulo_uses_integer_mode(self):
        generated = run_source(": : print ( mod ( 5 2 ) ) ; ", "1")
        self.assertIn("%", generated)
        self.assertNotIn("float", generated)

    def test_nested_terms_and_unary_negation(self):
        run_source(": : print ( neg ( add ( 2 mul ( 3 4 ) ) ) ) ; ", "-14")

    def test_assignment_computes_rhs_before_overwriting_target(self):
        run_source("#x : : #x = 4 ; #x = add ( #x 1 ) ; print ( #x ) ; ", "5")

    def test_nested_self_reading_assignment(self):
        run_source("#x : : #x = 3 ; #x = mul ( add ( #x 2 ) sub ( #x 1 ) ) ; print ( #x ) ; ", "10")

    def test_simple_name_and_signed_numeric_literals(self):
        run_source("#x : : #x = -7 ; print ( #x ) ; print ( neg ( -2 ) ) ; ", "-72")

    def test_exact_string_output_empty_string_and_print_order(self):
        run_source(': : print "a" ; print "" ; print "b?!" ; ', "ab?!")

    def test_nop_and_comment_have_no_runtime_output(self):
        run_source(': : nop ; comment "elsenot-spltmp10" ; nop ; ', "")

    def test_root_variable_and_same_spelling_parameter_use_distinct_symbol_identity(self):
        source = "#x : num #f ( #x ) { : : return ( #x ) } : print ( #x ) ; "
        checked = checked_source(source)
        p_node = checked.resolved.tree.get_node(checked.resolved.tree.root.child_ids[0])
        parts = program_parts(checked.resolved.tree, p_node.node_id)
        root_decl = next(iter(iter_list_items(checked.resolved.tree, parts.variables.node_id)))
        root_symbol_id = checked.resolved.binding_by_name_node[root_decl.node_id]
        function_node = next(
            node for node in checked.resolved.tree.iter_nodes()
            if node.kind is NodeKind.INNER and node.contents == "F_TYPE"
        )
        fparts = function_parts(checked.resolved.tree, function_node.node_id)
        parameter_leaf = next(iter(iter_list_items(checked.resolved.tree, fparts.parameters.node_id)))
        parameter_symbol_id = checked.resolved.binding_by_name_node[parameter_leaf.node_id]
        self.assertNotEqual(root_symbol_id, parameter_symbol_id)

        context = CodegenContext(checked)
        expansion_storage = context.new_storage(StorageKind.EXPANSION)
        destination = context.new_temp()
        generator = CodeGenerator(checked, context=context)
        fragment = generator.emit_term(
            fparts.return_term.node_id,
            destination,
            {parameter_symbol_id: expansion_storage},
        )
        from spl_frontend.codegen_ir import combine_fragments
        assembled = combine_fragments(
            # The root #x is assigned 4, but the #x in the return TERM must map
            # to the function parameter's distinct expansion storage (set to 9).
            IRFragment((expansion_storage, destination), (
                Assign(SymbolRef(root_symbol_id), NumberLiteral("4")),
                Assign(expansion_storage, NumberLiteral("9")),
            )),
            fragment,
            IRFragment(instructions=(PrintNumber(destination),)),
        )
        root_scope = checked.resolved.scope_by_node[p_node.node_id]
        target = TargetProgram(
            checked.numeric_mode,
            root_scope,
            checked.resolved.symbols,
            (root_symbol_id,),
            assembled,
        )
        _compile, execution = compile_and_run_target(render_target(target))
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertEqual(execution.stdout, "9")

    def test_call_without_inliner_is_a_structured_error(self):
        checked = checked_source(": num #f ( ) { : : return ( 5 ) } : print ( #f ( ) ) ; ")
        with self.assertRaisesRegex(CodegenError, "no inliner CallEmitter"):
            generate_target(checked)

    def test_call_hook_is_explicit_and_receives_result_destination(self):
        class StubCallEmitter:
            def __init__(self):
                self.destinations = []

            def emit_call(self, call_node_id, destination, environment, context):
                self.destinations.append(destination)
                if destination is None:
                    return IRFragment(instructions=(Comment("test stub void call"),))
                return IRFragment(instructions=(Assign(destination, NumberLiteral("42")),))

        stub = StubCallEmitter()
        checked = checked_source(": num #f ( ) { : : return ( 5 ) } : print ( #f ( ) ) ; ")
        target = render_target(generate_target(checked, call_emitter=stub))
        _compile, execution = compile_and_run_target(target)
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertEqual(execution.stdout, "42")
        self.assertEqual(len(stub.destinations), 1)
        self.assertIsNotNone(stub.destinations[0])


if __name__ == "__main__":
    unittest.main()
