"""Prove the acceptance harness detects the specific dangerous lowering faults."""
from dataclasses import replace
from pathlib import Path
import re
import tempfile
import unittest

from spl_frontend.codegen_ir import Assign, BinaryAssign, StorageKind, StorageRef, ConditionalJump
from spl_frontend.inlining import generate_program
from spl_frontend.target_writer import render_target
from tools.test_generated_target import verify_case
from tests.codegen_support import TARGET_CXX
from tests.unit.test_function_templates import checked


@unittest.skipUnless(TARGET_CXX, 'C++ compiler required for fault-sensitivity tests')
class TargetRegressionSensitivityTests(unittest.TestCase):
    def assert_rejected(self, source, expected, target, stage='output-mismatch'):
        with tempfile.TemporaryDirectory() as temporary:
            report = verify_case(source, expected, target_compiler=TARGET_CXX,
                                 pre_generated_target=target, artifacts=Path(temporary))
            self.assertFalse(report.passed)
            self.assertEqual(report.failure_stage, stage, report.to_json())
            if stage == 'output-mismatch':
                self.assertEqual(report.target_structure_status, 'passed')
                self.assertEqual(report.target_compile_status, 0)
                self.assertEqual(report.execution_status, 0)
            return report

    def test_wrong_boolean_false_destination_is_behaviorally_detected(self):
        source = ': : if or ( not ( eq ( 1 1 ) ) eq ( 1 2 ) ) then { print "bad" ; } else { print "ok" ; } ; '
        program = generate_program(checked(source))
        instructions = tuple(replace(i, false_target=i.true_target) if isinstance(i, ConditionalJump) else i
                             for i in program.fragment.instructions)
        target = render_target(replace(program, fragment=replace(program.fragment, instructions=instructions)))
        self.assert_rejected(source, 'ok', target)

    def test_reversed_formal_copy_is_behaviorally_detected(self):
        source = ': num #id ( #a ) { : : return ( #a ) } : print ( #id ( 7 ) ) ; '
        program = generate_program(checked(source))
        instructions = list(program.fragment.instructions)
        copies = [index for index,i in enumerate(instructions) if isinstance(i, Assign)
                  and isinstance(i.target, StorageRef) and i.target.kind is StorageKind.EXPANSION
                  and isinstance(i.value, StorageRef) and i.value.kind is StorageKind.CAPTURE]
        self.assertEqual(len(copies), 1)
        index = copies[0]
        original = instructions[index]
        instructions[index] = Assign(original.value, original.target)
        target = render_target(replace(program, fragment=replace(program.fragment, instructions=tuple(instructions))))
        report = self.assert_rejected(source, '7', target)
        self.assertEqual(report.stdout, '0')

    def test_stale_parent_capture_is_behaviorally_detected(self):
        source = '#x : num #f ( #a ) { #v : void #g ( ) { : : #v = add ( #v 1 ) ; return } : #v = #a ; #g ( ) ; return ( #v ) } : #x = #f ( 4 ) ; print ( #x ) ; print ":" ; #x = #f ( 8 ) ; print ( #x ) ; '
        program = generate_program(checked(source))
        instructions = list(program.fragment.instructions)
        writes = [index for index,i in enumerate(instructions) if isinstance(i, BinaryAssign)
                  and isinstance(i.target, StorageRef) and i.target.kind is StorageKind.EXPANSION]
        self.assertEqual(len(writes), 2)
        instructions[writes[1]] = replace(instructions[writes[1]], target=instructions[writes[0]].target)
        target = render_target(replace(program, fragment=replace(program.fragment, instructions=tuple(instructions))))
        report = self.assert_rejected(source, '5:9', target)
        self.assertEqual(report.stdout, '5:8')

    def test_reused_label_is_detected_before_native_compilation(self):
        source = ': : if eq ( 1 1 ) then { nop ; } else { nop ; } ; '
        target = render_target(generate_program(checked(source)))
        labels = re.findall(r'^spl_lbl_[0-9]+(?=:)', target, flags=re.M)
        self.assertGreaterEqual(len(labels), 2)
        bad = re.sub(r'^'+re.escape(labels[1])+':', labels[0]+':', target, flags=re.M)
        report = self.assert_rejected(source, '', bad, 'target-structure')
        self.assertIn('TARGET-DUPLICATE-LABEL', {issue['code'] for issue in report.target_issues})
        self.assertIsNone(report.target_compile_status)
