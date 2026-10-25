"""Part 3b behavior through the actual lexer, semantics, IR, C++ and process.

Expected outputs are explicit and independent of the inlining implementation.
No packaged compiler or native release artifact is built by this suite.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from spl_frontend.inlining import generate_program
from spl_frontend.codegen_ir import Label, StorageKind
from spl_frontend.target_writer import render_target
from tests.unit.test_function_templates import checked
from tools.target_inspector import inspect_target, tokenize_cpp_executable


CXX = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")


@unittest.skipUnless(CXX, "A C++ compiler is required to execute generated targets.")
class CodegenCallExecutionTests(unittest.TestCase):
    def execute(self, text, expected):
        program = generate_program(checked(text))
        target = render_target(program)
        program.validate()
        labels = [instruction.label for instruction in program.fragment.instructions if isinstance(instruction, Label)]
        self.assertEqual(len(labels), len(set(labels)))
        # The specification places the inactive mine before main. Inspect
        # executable tokens regardless of the writer's comment placement.
        self.assertEqual(inspect_target(target), ())
        with tempfile.TemporaryDirectory(prefix="spl-call-tests-") as directory:
            source = Path(directory) / "program.cpp"
            binary = Path(directory) / "program"
            source.write_text(target)
            compiled = subprocess.run([CXX, "-std=c++11", "-pedantic-errors", str(source), "-o", str(binary)],
                                      capture_output=True, text=True, timeout=30)
            self.assertEqual(compiled.returncode, 0, compiled.stderr + "\n" + target)
            run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout, expected)
            self.assertEqual(run.stderr, "")
        return program, target

    def test_zero_and_one_argument_return_nonzero_value_copy(self):
        self.execute(
            '#x : num #zero ( ) { : : return ( 7 ) } '
            'num #one ( #p ) { : : return ( #p ) } : '
            '#x = #one ( #zero ( ) ) ; print ( #x ) ; ', "7"
        )

    def test_deep_actual_call_chain_uses_the_backend_work_stack(self):
        source = ': num #id ( #a ) { : : return ( #a ) } : print ( '
        source += '#id ( ' * 180 + '42 ' + ') ' * 180 + ') ; '
        self.execute(source, "42")

    def test_multiple_whole_term_actuals(self):
        self.execute(
            ': num #f ( #a #b #c ) { : : return ( add ( mul ( #a 100 ) add ( mul ( #b 10 ) #c ) ) ) } '
            ': print ( #f ( add ( 1 1 ) mul ( 1 3 ) neg ( -4 ) ) ) ; ', "234"
        )

    def test_all_actuals_are_captured_before_later_argument_side_effects(self):
        self.execute(
            '#global : num #combine ( #a #b ) { : : return ( add ( mul ( #a 10 ) #b ) ) } '
            'num #bump ( ) { : : #global = add ( #global 1 ) ; return ( #global ) } : '
            '#global = 4 ; print ( #combine ( #global #bump ( ) ) ) ; '
            'print ":" ; print ( #global ) ; ', "45:5"
        )

    def test_actuals_evaluate_left_to_right(self):
        self.execute(
            ': num #combine ( #a #b ) { : : return ( add ( mul ( #a 10 ) #b ) ) } '
            'num #left ( ) { : : print "a" ; return ( 2 ) } '
            'num #right ( ) { : : print "b" ; return ( 3 ) } : '
            'print ( #combine ( #left ( ) #right ( ) ) ) ; ', "ab23"
        )

    def test_child_updates_current_parent_local_on_each_call(self):
        self.execute(
            '#x : num #f ( #a ) { #v : void #g ( ) { : : '
            '#v = add ( #v 1 ) ; return } : #v = #a ; #g ( ) ; return ( #v ) } : '
            '#x = #f ( 4 ) ; print ( #x ) ; print ":" ; '
            '#x = #f ( 8 ) ; print ( #x ) ; ', "5:9"
        )

    def test_nested_parent_shadow_does_not_detach_global(self):
        self.execute(
            '#x : num #f ( #a ) { #x : void #g ( ) { : : '
            '#x = add ( #x 1 ) ; return } : #x = #a ; #g ( ) ; return ( #x ) } : '
            '#x = 90 ; print ( #f ( 4 ) ) ; print ":" ; print ( #x ) ; ', "5:90"
        )

    def test_grandchild_updates_current_grandparent_and_global(self):
        self.execute(
            '#global : num #f ( #a ) { #local : void #g ( ) { : '
            'void #h ( ) { : : #local = add ( #local 2 ) ; '
            '#global = add ( #global 1 ) ; return } : #h ( ) ; return } '
            ': #local = #a ; #g ( ) ; return ( #local ) } : '
            '#global = 0 ; print ( #f ( 4 ) ) ; print ":" ; '
            'print ( #f ( 8 ) ) ; print ":" ; print ( #global ) ; ', "6:10:2"
        )

    def test_repeated_loop_function_has_fresh_jump_targets(self):
        program, _ = self.execute(
            ': num #count ( #n ) { #i : : #i = 0 ; '
            'while lesser ( #i #n ) do { #i = add ( #i 1 ) ; } ; '
            'return ( #i ) } : print ( #count ( 2 ) ) ; '
            'print ":" ; print ( #count ( 3 ) ) ; ', "2:3"
        )
        self.assertGreaterEqual(sum(isinstance(i, Label) for i in program.fragment.instructions), 6)

    def test_calls_in_assignment_print_arithmetic_comparison_actual_and_return(self):
        self.execute(
            '#x : num #identity ( #a ) { : : return ( #a ) } '
            'num #outer ( #p ) { : num #inner ( #q ) { : : return ( add ( #q 1 ) ) } '
            ': return ( #inner ( #p ) ) } : '
            '#x = #identity ( 3 ) ; print ( #x ) ; print ":" ; '
            'print ( add ( #identity ( 4 ) #identity ( 5 ) ) ) ; print ":" ; '
            'if eq ( #identity ( 6 ) 6 ) then { print "yes" ; } else { print "no" ; } ; '
            'print ":" ; print ( #identity ( #outer ( 7 ) ) ) ; ', "3:9:yes:8"
        )

    def test_void_procedure_returns_no_numeric_value_and_preserves_root_write(self):
        program, _ = self.execute(
            '#x : void #set ( #value ) { : : #x = #value ; return } : '
            '#x = 0 ; #set ( 7 ) ; print ( #x ) ; ', "7"
        )
        self.assertFalse(any(s.kind is StorageKind.RETURN for s in program.fragment.declarations))

    def test_uncalled_function_code_mine_produces_no_output_or_state_change(self):
        self.execute(
            '#x : void #unused ( ) { : : print "bad" ; #x = 99 ; nop ; '
            'comment "inside.mine" ; return } : #x = 4 ; print ( #x ) ; ', "4"
        )

    def test_mine_annotations_are_comment_safe_and_target_still_compiles(self):
        _, target = self.execute(
            ': void #f ( ) { : : nop ; comment "comment!" ; return } : #f ( ) ; ', ""
        )
        self.assertIn("// nop", target)
        self.assertLess(target.index("BEGIN CODE MINE"), target.index("int main()"))

    def test_short_circuit_skips_calls_and_loop_conditions_reevaluate_them(self):
        self.execute(
            '#x : num #tick ( ) { : : #x = add ( #x 1 ) ; return ( #x ) } : '
            '#x = 0 ; if or ( eq ( 1 1 ) eq ( #tick ( ) 1 ) ) then { } else { } ; '
            'if and ( eq ( 1 2 ) eq ( #tick ( ) 1 ) ) then { } else { } ; '
            'print ( #x ) ; print ":" ; '
            'while lesser ( #tick ( ) 3 ) do { print ( #x ) ; } ; print ( #x ) ; ',
            '0:123',
        )

    def test_repeated_compilations_are_deterministic_and_independent(self):
        text = ': num #f ( #a ) { : : return ( add ( #a 1 ) ) } : print ( #f ( 8 ) ) ; '
        _, first = self.execute(text, "9")
        self.execute(': void #f ( ) { : : print "other" ; return } : #f ( ) ; ', "other")
        _, last = self.execute(text, "9")
        self.assertEqual(first, last)

    def test_float_arguments_locals_and_returns_use_one_selected_mode(self):
        _, target = self.execute(
            ': num #f ( #a ) { #local : : #local = add ( #a 0.5 ) ; return ( #local ) } '
            ': print ( #f ( 2.25 ) ) ; ', "2.75"
        )
        tokens = [t.value for t in tokenize_cpp_executable(target)]
        self.assertFalse(any(token == "int" and tokens[index + 1].startswith("spl_")
                             for index, token in enumerate(tokens[:-1])))
