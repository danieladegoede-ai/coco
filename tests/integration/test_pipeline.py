"""End-to-end integration tests for the SPL front end.

These tests exercise the full pipeline (generator, mutator, CLI, lexer,
parser, tree, XML writer) using the real modules. They complement the
unit tests by checking that the components work together.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from tools.generate_valid_spl import generate_program
from tools.mutate_spl import mutate_program


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


class PipelineIntegrationTests(unittest.TestCase):
    """Run the CLI as a subprocess against generated and mutated inputs."""

    def setUp(self) -> None:
        self._original_cwd = Path.cwd()
        self._temporary = tempfile.TemporaryDirectory()
        self.workdir = Path(self._temporary.name)
        os.chdir(self.workdir)

    def tearDown(self) -> None:
        os.chdir(self._original_cwd)
        self._temporary.cleanup()

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{SRC_ROOT}{os.pathsep}{existing}" if existing else str(SRC_ROOT)
        )
        return env

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "spl_frontend", *args],
            cwd=self.workdir,
            env=self._env(),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _write_input(self, text: str, name: str = "SPL.txt") -> Path:
        path = self.workdir / name
        path.write_bytes(text.encode("utf-8"))
        return path

    # ------------------------------------------------------------------
    # Positive cases
    # ------------------------------------------------------------------

    def test_generated_valid_programs_parse_across_seeds(self) -> None:
        for seed in range(1, 6):
            with self.subTest(seed=seed):
                text = generate_program(seed=seed)
                self._write_input(text)
                xml_path = self.workdir / "tree.xml"
                if xml_path.exists():
                    xml_path.unlink()
                completed = self._run_cli()
                self.assertEqual(
                    completed.returncode,
                    0,
                    f"seed {seed} failed: {completed.stderr}",
                )
                self.assertTrue(xml_path.exists(), "tree.xml missing")

    def test_generated_output_is_valid_xml(self) -> None:
        text = generate_program(seed=3)
        self._write_input(text)
        completed = self._run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        tree = ET.parse(self.workdir / "tree.xml")
        self.assertEqual(tree.getroot().tag, "syntax_tree")

    def test_explicit_input_path_is_used(self) -> None:
        text = generate_program(seed=3)
        custom = self._write_input(text, name="custom.txt")
        # No SPL.txt exists; CLI must use custom.txt.
        self.assertFalse((self.workdir / "SPL.txt").exists())
        completed = self._run_cli(str(custom))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((self.workdir / "tree.xml").exists())

    # ------------------------------------------------------------------
    # Negative cases via mutation
    # ------------------------------------------------------------------

    def test_generated_invalid_programs_are_rejected(self) -> None:
        valid = generate_program(seed=3)
        for seed in range(1, 6):
            with self.subTest(seed=seed):
                mutation = mutate_program(valid, seed=seed)
                self._write_input(mutation.program)
                completed = self._run_cli()
                self.assertNotEqual(
                    completed.returncode,
                    0,
                    f"mutation {mutation.kind.value} was accepted",
                )

    def test_diagnostics_have_no_traceback(self) -> None:
        valid = generate_program(seed=3)
        for seed in range(1, 6):
            with self.subTest(seed=seed):
                mutation = mutate_program(valid, seed=seed)
                self._write_input(mutation.program)
                completed = self._run_cli()
                self.assertNotIn(
                    "Traceback",
                    completed.stderr,
                    f"mutation {mutation.kind.value} raised a traceback",
                )

    def test_explicit_path_appears_in_diagnostic(self) -> None:
        valid = generate_program(seed=3)
        mutation = mutate_program(valid, seed=5)
        custom = self._write_input(mutation.program, name="broken.txt")
        completed = self._run_cli(str(custom))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "broken.txt",
            completed.stderr,
            "diagnostic did not include the explicit input path",
        )

    # ------------------------------------------------------------------
    # Output lifecycle
    # ------------------------------------------------------------------

    def test_invalid_run_removes_xml_from_previous_run(self) -> None:
        # Valid run first.
        valid = generate_program(seed=3)
        self._write_input(valid)
        first = self._run_cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        xml_path = self.workdir / "tree.xml"
        self.assertTrue(xml_path.is_file())

        # Invalid run in the same directory.
        mutation = mutate_program(valid, seed=5)
        self._write_input(mutation.program)
        second = self._run_cli()
        self.assertNotEqual(second.returncode, 0)

        self.assertFalse(xml_path.exists())

    def test_valid_run_after_invalid_run_publishes_fresh_xml(self) -> None:
        self._write_input(": ")
        self.assertNotEqual(self._run_cli().returncode, 0)
        xml_path = self.workdir / "tree.xml"
        self.assertFalse(xml_path.exists())

        self._write_input(": : ")
        completed = self._run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(ET.parse(xml_path).getroot().tag, "syntax_tree")


if __name__ == "__main__":
    unittest.main()
