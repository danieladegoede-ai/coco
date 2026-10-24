"""Target writer serialization and native-compiler smoke tests."""

import tempfile
from dataclasses import replace
import unittest
from unittest.mock import patch
from pathlib import Path

from spl_frontend.codegen import generate_target
from spl_frontend.codegen_ir import (
    CodeMineSection, CodegenError, Comment, IRFragment, Label, FreshNameAllocator,
    NumberLiteral, PrintNumber, PrintString, StorageRef, StringLiteral, UnaryAssign, UnaryOperator,
)
from spl_frontend.semantic_model import NumericMode
from spl_frontend.target_writer import render_target, write_target
from tests.codegen_support import checked_source, compile_and_run_target, TARGET_CXX


@unittest.skipUnless(TARGET_CXX, "a C++ compiler is required for target writer smoke tests")
class TargetWriterTests(unittest.TestCase):
    def test_unary_negative_literal_does_not_become_a_decrement_token(self):
        storage = StorageRef(1)
        program = replace(generate_target(checked_source(": : ")), fragment=IRFragment(
            (storage,), (UnaryAssign(storage, UnaryOperator.NEGATE, NumberLiteral("-2")), PrintNumber(storage)),
        ))
        _compile, execution = compile_and_run_target(render_target(program))
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertEqual(execution.stdout, "2")

    def test_comment_backslash_cannot_swallow_the_following_statement(self):
        program = replace(generate_target(checked_source(": : ")), fragment=IRFragment(instructions=(
            Comment("comment ends with a backslash \\"), PrintString(StringLiteral("visible")),
        )))
        _compile, execution = compile_and_run_target(render_target(program))
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertEqual(execution.stdout, "visible")

    def test_minimal_program_is_valid_and_has_exactly_one_main_and_return(self):
        checked = checked_source(": : ")
        target = render_target(generate_target(checked))
        self.assertEqual(target.count("int main()"), 1)
        self.assertEqual(target.count("return 0;"), 1)
        self.assertRegex(target, r"return 0;\n}\n\Z")
        _compile, execution = compile_and_run_target(target)
        self.assertEqual(execution.returncode, 0)
        self.assertEqual(execution.stdout, "")
        self.assertEqual(execution.stderr, "")

    def test_generated_names_are_deterministic_between_compilations(self):
        source = "#x : : #x = add ( 1 2 ) ; print ( #x ) ; "
        first = render_target(generate_target(checked_source(source)))
        second = render_target(generate_target(checked_source(source)))
        self.assertEqual(first, second)
        self.assertIn("int spl_v1{};", first)
        self.assertIn("int spl_tmp_1{};", first)

    def test_float_mode_uses_float_storage_and_literals(self):
        target = render_target(generate_target(checked_source(": : print ( div ( 5 2 ) ) ; ")))
        self.assertIn("float spl_tmp_1{};", target)
        self.assertIn("spl_tmp_2 = 5.0f;", target)
        _compile, execution = compile_and_run_target(target)
        self.assertEqual(execution.stdout, "2.5")

    def test_terminal_and_adjacent_labels_are_legal(self):
        checked = checked_source(": : ")
        root = checked.resolved.tree.root
        assert root is not None
        scope_id = checked.resolved.scope_by_node[root.child_ids[0]]
        allocator = FreshNameAllocator()
        label1 = allocator.new_label()
        label2 = allocator.new_label()
        from spl_frontend.codegen_ir import TargetProgram
        program = TargetProgram(
            NumericMode.INTEGER, scope_id, checked.resolved.symbols, (),
            IRFragment(instructions=(Label(label1), Label(label2))),
        )
        target = render_target(program)
        self.assertIn("spl_lbl_1: ;", target)
        self.assertIn("spl_lbl_2: ;", target)
        _compile, execution = compile_and_run_target(target)
        self.assertEqual(execution.stdout, "")

    def test_template_code_mine_is_safely_non_executable(self):
        checked = checked_source(": : ")
        from spl_frontend.codegen_ir import TargetProgram
        root = checked.resolved.tree.root
        assert root is not None
        scope_id = checked.resolved.scope_by_node[root.child_ids[0]]
        program = TargetProgram(
            NumericMode.INTEGER,
            scope_id,
            checked.resolved.symbols,
            (),
            IRFragment(),
            (CodeMineSection("function template", "/* template close */\nelse not || #x"),),
        )
        target = render_target(program)
        self.assertIn("// /* template close */", target)
        self.assertIn("// else not || #x", target)
        _compile, execution = compile_and_run_target(target)
        self.assertEqual(execution.returncode, 0)
        self.assertEqual(execution.stdout, "")

    def test_write_target_is_atomic_and_creates_requested_file(self):
        checked = checked_source(": : ")
        program = generate_target(checked)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "program.cpp"
            path.write_text("old target", encoding="utf-8")
            write_target(program, path)
            self.assertEqual(path.read_text(encoding="utf-8"), render_target(program))
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_failed_atomic_replace_preserves_original_file_and_diagnostic(self):
        checked = checked_source(": : ")
        target_program = generate_target(checked)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "program.cpp"
            path.write_text("previous valid target", encoding="utf-8")
            with patch("spl_frontend.target_writer.os.replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaisesRegex(CodegenError, "Cannot write target output"):
                    write_target(target_program, path)
            self.assertEqual(path.read_text(encoding="utf-8"), "previous valid target")
            self.assertEqual(list(Path(directory).glob(".*.tmp")), [])

    def test_writer_rejects_missing_output_directory_without_creating_it(self):
        checked = checked_source(": : ")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing" / "program.cpp"
            with self.assertRaisesRegex(Exception, "Output directory does not exist"):
                write_target(generate_target(checked), path)
            self.assertFalse(path.parent.exists())


if __name__ == "__main__":
    unittest.main()
