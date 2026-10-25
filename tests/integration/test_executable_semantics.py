"""Compile-and-run acceptance corpus and failure-evidence contract (#34)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.test_generated_target import run_manifest, verify_case
from tests.codegen_support import TARGET_CXX

MANIFEST = ROOT / "tests/fixtures/codegen/acceptance/cases.json"


@unittest.skipUnless(TARGET_CXX, "a C++ compiler is required for executable semantics tests")
class ExecutableSemanticsAcceptanceTests(unittest.TestCase):
    def test_expected_source_error_keeps_real_diagnostic_without_traceback(self):
        with tempfile.TemporaryDirectory(prefix="spl-source-error-") as temporary:
            report = verify_case(
                ': : print ( ) ; ', "", case_id="syntax-error", target_compiler=TARGET_CXX,
                artifacts=Path(temporary),
            )
            self.assertFalse(report.passed)
            self.assertEqual(report.failure_stage, "compiler-process")
            self.assertNotEqual(report.compiler_status, 0)
            self.assertIn("SPL.txt:1:", report.compiler_stderr)
            self.assertIn("syntax[", report.compiler_stderr)
            self.assertNotIn("Traceback", report.compiler_stderr)
            self.assertIsNone(report.target_compile_status)

    def test_successful_external_process_must_publish_a_target(self):
        with tempfile.TemporaryDirectory(prefix="spl-missing-target-") as temporary:
            report = verify_case(
                ": : ", "", case_id="missing-target", target_compiler=TARGET_CXX,
                compiler_command=[sys.executable, "-c", "from pathlib import Path; Path('program.cpp').mkdir()"], artifacts=Path(temporary),
            )
            self.assertFalse(report.passed)
            self.assertEqual(report.compiler_status, 0)
            self.assertEqual(report.failure_stage, "compiler-output-missing")
            self.assertIsNone(report.target_compile_status)
            self.assertTrue((Path(report.artifact_dir) / "reproduce.sh").is_file())

    def test_structural_failures_stop_before_target_compilation(self):
        target = 'int main() { goto missing; return 0; }\n'
        with tempfile.TemporaryDirectory(prefix="spl-structural-error-") as temporary:
            report = verify_case(
                ": : ", "", case_id="dangling-goto", target_compiler=TARGET_CXX,
                pre_generated_target=target, artifacts=Path(temporary),
            )
            self.assertFalse(report.passed)
            self.assertEqual(report.failure_stage, "target-structure")
            self.assertIsNone(report.target_compile_status)
            self.assertIn("TARGET-DANGLING-GOTO", {item["code"] for item in report.target_issues})

    def test_all_hand_computed_backend_anchors_compile_and_execute(self):
        reports, summary = run_manifest(MANIFEST, artifacts=ROOT/'build/acceptance-failures',
                                        target_compiler=TARGET_CXX, timeout=5.0, seed=20261023)
        self.assertEqual(summary["blocked"], [])
        self.assertEqual(summary["runnable"], len(json.loads(MANIFEST.read_text())["cases"]))
        self.assertEqual(summary["passed"], summary["runnable"], [report.to_json() for report in reports if not report.passed])
        self.assertEqual(summary["failed"], 0)
        self.assertTrue(all(report.compiler_status == 0 for report in reports))
        self.assertTrue(all(report.target_compile_status == 0 for report in reports))
        self.assertTrue(all(report.execution_status == 0 for report in reports))
        self.assertTrue(all(report.stdout_matches is True for report in reports))

    def test_requirement_matrix_covers_original_38_ids_with_real_evidence(self):
        matrix_path = ROOT / "tests/fixtures/codegen/requirements.json"
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        requirements = matrix["requirements"]
        ids = [entry["id"] for entry in requirements]
        expected = [f"N{i:02d}" for i in range(1, 11)]
        expected += [f"T{i:02d}" for i in range(1, 11)]
        expected += [f"G{i:02d}" for i in range(1, 11)]
        expected += [f"F{i:02d}" for i in range(1, 9)]
        self.assertEqual(len(requirements), 38)
        self.assertEqual(ids, expected)
        status_by_id = {entry["id"]: entry["status"] for entry in requirements}
        self.assertTrue(all(status == "implemented-tested" for status in status_by_id.values()))
        import ast
        semantic_ids = {c['id'] for c in json.loads((ROOT/'tests/fixtures/semantics/cases.json').read_text())['cases']}
        target_ids = {c['id'] for c in json.loads(MANIFEST.read_text())['cases']}
        for row in requirements:
            self.assertTrue(row['tests'], row['id'])
            self.assertTrue(row['semantic_cases'] or row['target_cases'], row['id'])
            self.assertTrue(set(row['semantic_cases']).issubset(semantic_ids))
            self.assertTrue(set(row['target_cases']).issubset(target_ids))
            for reference in row['tests']:
                filename, method = reference.split('::')
                methods = {n.name for n in ast.walk(ast.parse((ROOT/filename).read_text())) if isinstance(n,ast.FunctionDef)}
                self.assertIn(method, methods, (row['id'], reference))

    def test_original_ten_planning_anchors_keep_correct_error_and_runtime_expectations(self):
        anchors = json.loads((MANIFEST.parent/'planning_anchors.json').read_text())['anchors']
        self.assertEqual([a['id'] for a in anchors], [f'E{i:02}' for i in range(1,11)])
        semantic_root = ROOT/'tests/fixtures/semantics'
        semantic = {c['id']:c for c in json.loads((semantic_root/'cases.json').read_text())['cases']}
        targets = {c['id']:c for c in json.loads(MANIFEST.read_text())['cases']}
        for anchor in anchors:
            case = semantic[anchor['semantic_case']]
            self.assertEqual(case['expected_status'], anchor['expected_status'])
            self.assertEqual(case['expected_code'], anchor['expected_code'])
            if anchor['expected_status'] == 0:
                target = targets[anchor['target_case']]
                self.assertEqual(target['expected_stdout'], anchor['expected_stdout'])
                self.assertEqual((semantic_root/case['file']).read_text().split(), target['source'].split())
            else:
                self.assertNotIn('target_case', anchor)

    def test_structurally_legal_but_wrong_target_output_fails_and_keeps_artifacts(self):
        target = '#include <iostream>\nint main() { std::cout << "right"; return 0; }\n'
        with tempfile.TemporaryDirectory(prefix="spl-wrong-output-") as temporary:
            artifact_root = Path(temporary) / "evidence"
            report = verify_case(
                ": : ", "wrong", case_id="intentional-output-mismatch",
                target_compiler=TARGET_CXX, artifacts=artifact_root,
                pre_generated_target=target,
            )
            self.assertFalse(report.passed)
            self.assertEqual(report.failure_stage, "output-mismatch")
            self.assertEqual(report.target_structure_status, "passed")
            self.assertEqual(report.target_compile_status, 0)
            self.assertEqual(report.execution_status, 0)
            self.assertFalse(report.stdout_matches)
            saved = Path(report.artifact_dir or "")
            for file_name in ("input.spl", "program.cpp", "expected.stdout", "target-run.stdout.log", "report.json", "metadata.json"):
                self.assertTrue((saved / file_name).is_file(), file_name)
            saved_report = json.loads((saved / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_report["failure_stage"], "output-mismatch")

    def test_target_timeout_is_reported_and_reproducible(self):
        target = "int main() { spl_lbl_1: ; goto spl_lbl_1; return 0; }\n"
        with tempfile.TemporaryDirectory(prefix="spl-timeout-") as temporary:
            report = verify_case(
                ": : ", "", case_id="intentional-target-timeout", target_compiler=TARGET_CXX,
                execution_timeout=0.1, artifacts=Path(temporary), pre_generated_target=target,
            )
            self.assertFalse(report.passed)
            self.assertEqual(report.failure_stage, "target-timeout")
            self.assertEqual(report.target_compile_status, 0)
            self.assertEqual(report.execution_status, "timeout")
            saved = Path(report.artifact_dir or "")
            self.assertTrue((saved / "program.cpp").exists())
            self.assertTrue((saved / "reproduce.sh").is_file())
            self.assertEqual(report.reproduction_command, "sh reproduce.sh")
            replay = (saved / "reproduce.sh").read_text(encoding="utf-8")
            self.assertIn("--execution-timeout 0.1", replay)
            self.assertIn("Timed out", (saved / "target-run.stderr.log").read_text(encoding="utf-8"))

            # Verify the saved command is executable and preserves the same
            # failure classification instead of merely checking its contents.
            replay_result = subprocess.run(
                [sys.executable, str(saved/"reproduce.py")], cwd=saved, text=True, capture_output=True,
                timeout=15, check=False,
            )
            self.assertEqual(replay_result.returncode, 1, replay_result.stdout + replay_result.stderr)
            self.assertIn('"failure_stage": "target-timeout"', replay_result.stdout)

    def test_target_compilation_failure_is_separate_and_preserves_diagnostics(self):
        target = '#include <iostream>\nint main() { std::cout << missing_identifier; return 0; }\n'
        with tempfile.TemporaryDirectory(prefix="spl-target-compile-error-") as temporary:
            report = verify_case(
                ": : ", "", case_id="intentional-target-compile-error", target_compiler=TARGET_CXX,
                artifacts=Path(temporary), pre_generated_target=target,
            )
            self.assertFalse(report.passed)
            self.assertEqual(report.failure_stage, "target-compilation")
            self.assertEqual(report.compiler_status, "not-run")
            self.assertNotEqual(report.target_compile_status, 0)
            saved = Path(report.artifact_dir or "")
            self.assertTrue((saved / "program.cpp").exists())
            self.assertIn("missing_identifier", (saved / "target-compile.stderr.log").read_text(encoding="utf-8"))
            self.assertIn('missing_identifier', report.target_compile_stderr)
            replay = subprocess.run([sys.executable, str(saved/'reproduce.py')], capture_output=True, text=True, timeout=15)
            self.assertEqual(replay.returncode, 1, replay.stdout+replay.stderr)
            self.assertIn('"failure_stage": "target-compilation"', replay.stdout)
            self.assertTrue((saved / "reproduce.sh").is_file())

    def test_real_source_runtime_timeout_retains_full_compiler_evidence(self):
        source = ': : while eq ( 1 1 ) do { nop ; } ; '
        with tempfile.TemporaryDirectory() as temporary:
            report = verify_case(source, '', target_compiler=TARGET_CXX,
                                 execution_timeout=0.1, artifacts=Path(temporary))
            self.assertEqual(report.failure_stage, 'target-timeout')
            self.assertEqual(report.compiler_status, 0)
            self.assertEqual(report.target_compile_status, 0)
            self.assertEqual(report.execution_status, 'timeout')
            self.assertEqual((Path(report.artifact_dir)/'input.spl').read_text(), source)

    def test_external_compiler_failure_is_separate_from_target_compile_status(self):
        with tempfile.TemporaryDirectory(prefix="spl-compiler-failure-") as temporary:
            artifacts = Path(temporary) / "evidence"
            report = verify_case(
                ": : ", "", case_id="intentional-compiler-failure", target_compiler=TARGET_CXX,
                compiler_command=[os.path.relpath(sys.executable), "-c", "import sys; print('compiler fixture failure'); sys.exit(7)"],
                artifacts=artifacts,
            )
            self.assertFalse(report.passed)
            self.assertEqual(report.failure_stage, "compiler-process")
            self.assertEqual(report.compiler_status, 7)
            self.assertIsNone(report.target_compile_status)
            self.assertIn("compiler fixture failure", report.compiler_stdout)
            saved = Path(report.artifact_dir or "")
            self.assertTrue((saved / "compiler.stdout.log").exists())
            self.assertTrue((saved / "compiler.stderr.log").exists())
            replay = subprocess.run([sys.executable, str(saved/'reproduce.py')], capture_output=True, text=True, timeout=10)
            self.assertEqual(replay.returncode, 1, replay.stdout+replay.stderr)
            self.assertIn('"compiler_status": 7', replay.stdout)


if __name__ == "__main__":
    unittest.main()
