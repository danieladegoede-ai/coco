"""Real compiler smoke tests for the target program skeleton (#26)."""

from __future__ import annotations

import unittest

from spl_frontend.codegen import generate_target
from spl_frontend.codegen_ir import CodeMineSection, IRFragment, TargetProgram
from spl_frontend.semantic_model import NumericMode
from spl_frontend.target_writer import render_target
from tests.codegen_support import TARGET_CXX, checked_source, compile_and_run_target


@unittest.skipUnless(TARGET_CXX, "a C++ compiler is required for target skeleton tests")
class TargetSkeletonIntegrationTests(unittest.TestCase):
    def test_empty_spl_program_compiles_and_runs_without_output(self):
        target = render_target(generate_target(checked_source(": : ")))
        compilation, execution = compile_and_run_target(target)
        self.assertEqual(compilation.returncode, 0, compilation.stderr)
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertEqual(execution.stdout, "")

    def test_root_variables_and_generated_temporaries_are_hoisted_and_typed(self):
        checked = checked_source("#x : : #x = div ( 5 2 ) ; print ( #x ) ; ")
        target = render_target(generate_target(checked))
        import re
        variable_declaration = re.search(r"^    float spl_v[0-9]+\{\};$", target, re.MULTILINE)
        temporary_declaration = re.search(r"^    float spl_tmp_[0-9]+\{\};$", target, re.MULTILINE)
        self.assertIsNotNone(variable_declaration, target)
        self.assertIsNotNone(temporary_declaration, target)
        self.assertLess(variable_declaration.start(), target.index("spl_v", variable_declaration.end()))
        self.assertLess(temporary_declaration.start(), target.index("std::cout"))
        compilation, execution = compile_and_run_target(target)
        self.assertEqual(compilation.returncode, 0, compilation.stderr)
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertEqual(execution.stdout, "2.5")

    def test_comments_in_template_code_mine_cannot_terminate_a_comment_block(self):
        checked = checked_source(": : ")
        root = checked.resolved.tree.root
        assert root is not None
        p_id = root.child_ids[0]
        scope_id = checked.resolved.scope_by_node[p_id]
        program = TargetProgram(
            NumericMode.INTEGER, scope_id, checked.resolved.symbols, (), IRFragment(),
            (CodeMineSection("sample", "*/ else not ; goto spl_lbl_1;\nint main() { }"),),
        )
        target = render_target(program)
        self.assertNotIn("/*", target)
        self.assertIn("// */ else not ; goto spl_lbl_1;", target)
        compilation, execution = compile_and_run_target(target)
        self.assertEqual(compilation.returncode, 0, compilation.stderr)
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertEqual(execution.stdout, "")


if __name__ == "__main__":
    unittest.main()
