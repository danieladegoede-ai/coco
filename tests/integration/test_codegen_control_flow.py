"""Native execution tests for Boolean, branch and all loop translations."""

import unittest
from dataclasses import replace

from spl_frontend.codegen import CodeGenerator, CodegenContext, generate_target
from spl_frontend.codegen_ir import (
    Assign, BinaryAssign, BinaryOperator, CodeMineSection, IRFragment, NumberLiteral,
    StorageKind, clone_fragment, combine_fragments,
)
from spl_frontend.target_writer import render_target
from spl_frontend.tree_walkers import function_parts, iter_list_items, program_parts
from tests.codegen_support import TARGET_CXX, checked_source, compile_and_run_target, run_source
from tools.target_inspector import inspect_target


def branch(condition: str, true_text: str = "t", false_text: str = "f") -> str:
    return f'if {condition} then {{ print "{true_text}" ; }} else {{ print "{false_text}" ; }} ; '


def atom(value: bool) -> str:
    return "eq ( 1 1 )" if value else "eq ( 1 2 )"


@unittest.skipUnless(TARGET_CXX, "a C++ compiler is required for executable codegen tests")
class CodegenControlFlowIntegrationTests(unittest.TestCase):
    def test_deep_source_accepted_by_the_parser_still_lowers_and_executes(self):
        condition = "not ( " * 701 + "eq ( 1 1 ) " + ") " * 701
        target = run_source(": : " + branch(condition), "f")
        self.assertEqual(inspect_target(target), ())

    def test_call_hook_preserves_operand_order_and_short_circuit_side_effects(self):
        # Handwritten hook fixture for one incrementing function, not a second
        # inliner. This tests the backend side of the public CallEmitter API.
        class TickEmitter:
            def emit_call(self, call_node_id, destination, environment, context):
                symbol_id = next(s.symbol_id for s in context.checked.resolved.symbols.values()
                                 if s.original_name == "#x")
                counter = context.resolve_symbol(symbol_id, environment)
                return IRFragment(instructions=(
                    BinaryAssign(counter, BinaryOperator.ADD, counter, NumberLiteral("1")),
                    Assign(destination, counter),
                ))

        source = (
            '#x : num #tick ( ) { : : #x = add ( #x 1 ) ; return ( #x ) } : '
            '#x = 0 ; print ( sub ( #tick ( ) #tick ( ) ) ) ; print ":" ; print ( #x ) ; '
            '#x = 0 ; '
            'if and ( eq ( 1 2 ) eq ( #tick ( ) 1 ) ) then { print "bad" ; } else { print "a" ; } ; '
            'if or ( eq ( 1 1 ) eq ( #tick ( ) 1 ) ) then { print "b" ; } else { print "bad" ; } ; '
            'if and ( eq ( 1 1 ) eq ( #tick ( ) 1 ) ) then { print "c" ; } else { print "bad" ; } ; '
            'if or ( eq ( 1 2 ) eq ( #tick ( ) 2 ) ) then { print "d" ; } else { print "bad" ; } ; '
            'if lesser ( #tick ( ) #tick ( ) ) then { print "t" ; } else { print "bad" ; } ; '
            'print ( #x ) ; '
        )
        target = run_source(source, "-1:2abcdt4", call_emitter=TickEmitter())
        self.assertEqual(inspect_target(target), ())

    def test_repeated_clones_of_a_loop_keep_storage_and_labels_disjoint(self):
        checked = checked_source(
            ': void #f ( ) { #i : : #i = 0 ; while lesser ( #i 3 ) do { '
            'print ( #i ) ; #i = add ( #i 1 ) ; } ; return } : '
        )
        tree = checked.resolved.tree
        function = next(node for node in tree.iter_nodes() if node.contents == "F_TYPE")
        parts = program_parts(tree, function_parts(tree, function.node_id).body.node_id)
        declaration = next(iter(iter_list_items(tree, parts.variables.node_id)))
        symbol_id = checked.resolved.binding_by_name_node[declaration.node_id]
        context = CodegenContext(checked)
        local = context.new_storage(StorageKind.EXPANSION)
        fragment = combine_fragments(
            IRFragment(declarations=(local,)),
            CodeGenerator(checked, context=context).emit_algorithm(parts.algorithm.node_id, {symbol_id: local}),
        )
        first = clone_fragment(fragment, context.allocator)
        second = clone_fragment(fragment, context.allocator)
        self.assertTrue(set(first.declarations).isdisjoint(second.declarations))
        program = replace(
            generate_target(checked, context=context), fragment=combine_fragments(first, second),
            code_mine=(CodeMineSection("hostile template", '*/ int main() {}\nelse && ! #x\\\n/*'),),
        )
        target = render_target(program)
        self.assertEqual(inspect_target(target), ())
        _compile, execution = compile_and_run_target(target)
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertEqual(execution.stdout, "012012")

    def test_and_or_truth_tables_not_and_all_comparisons(self):
        source = ": : "
        expected = ""
        for op, table in (("and", "tfff"), ("or", "tttf")):
            values = ((True, True), (True, False), (False, True), (False, False))
            for (left, right), result in zip(values, table):
                source += branch(f"{op} ( {atom(left)} {atom(right)} )")
                expected += result
        source += branch(f"not ( {atom(True)} )")
        source += branch(f"not ( {atom(False)} )")
        expected += "ft"
        for condition, result in (
            ("eq ( 1 1 )", "t"), ("eq ( 1 2 )", "f"),
            ("larger ( 2 1 )", "t"), ("larger ( 1 2 )", "f"),
            ("lesser ( 1 2 )", "t"), ("lesser ( 2 1 )", "f"),
        ):
            source += branch(condition)
            expected += result
        run_source(source, expected)

    def test_nested_not_and_or_false_fallthrough_anchor(self):
        source = (
            ': : if or ( not ( eq ( 1 1 ) ) eq ( 1 2 ) ) '
            'then { print "bad" ; } else { print "ok" ; } ; '
        )
        run_source(source, "ok")

    def test_nested_boolean_expressions(self):
        cases = (
            ("or ( not ( eq ( 1 1 ) ) eq ( 1 2 ) )", "f"),
            ("and ( not ( eq ( 1 2 ) ) eq ( 1 1 ) )", "t"),
            ("not ( and ( eq ( 1 1 ) eq ( 1 2 ) ) )", "t"),
            ("not ( or ( eq ( 1 2 ) eq ( 1 1 ) ) )", "f"),
        )
        source = ": : "
        expected = ""
        for expression, result in cases:
            source += branch(expression)
            expected += result
        run_source(source, expected)

    def test_all_four_loop_forms_zero_one_and_repeated_iterations(self):
        increment = "#x = add ( #x 1 ) ; "
        source = "#x : : "
        expected = ""
        # Pre-test while: false condition executes zero iterations; true condition repeats.
        source += "#x = 0 ; while eq ( 1 2 ) do { " + increment + "} ; print ( #x ) ; "
        expected += "0"
        source += "#x = 0 ; while lesser ( #x 3 ) do { " + increment + "} ; print ( #x ) ; "
        expected += "3"
        # Pre-test until: true condition exits immediately; false condition repeats.
        source += "#x = 0 ; until eq ( 1 1 ) do { " + increment + "} ; print ( #x ) ; "
        expected += "0"
        source += "#x = 0 ; until eq ( #x 3 ) do { " + increment + "} ; print ( #x ) ; "
        expected += "3"
        # Post-test forms always execute once, even when their condition asks to stop.
        source += "#x = 0 ; do { " + increment + "} while lesser ( #x 0 ) ; print ( #x ) ; "
        expected += "1"
        source += "#x = 0 ; do { " + increment + "} while lesser ( #x 3 ) ; print ( #x ) ; "
        expected += "3"
        source += "#x = 0 ; do { " + increment + "} until eq ( #x 1 ) ; print ( #x ) ; "
        expected += "1"
        source += "#x = 0 ; do { " + increment + "} until eq ( #x 3 ) ; print ( #x ) ; "
        expected += "3"
        run_source(source, expected, timeout=3.0)

    def test_nested_branch_inside_loop_preserves_control_flow(self):
        source = (
            '#x : : #x = 0 ; '
            'while lesser ( #x 4 ) do { '
            'if eq ( mod ( #x 2 ) 0 ) then { print "e" ; } else { print "o" ; } ; '
            '#x = add ( #x 1 ) ; '
            '} ; '
        )
        run_source(source, "eoeo", timeout=3.0)
