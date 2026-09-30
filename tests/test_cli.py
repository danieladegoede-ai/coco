"""End-to-end tests for the SPL front-end CLI."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from xml.etree import ElementTree as ET

from spl_frontend.cli import main
from spl_frontend.diagnostics import ExitCode


MINIMAL_VALID = ": : "


class CliTestCase(unittest.TestCase):
    """Base class that runs each test in its own temporary directory."""

    def setUp(self) -> None:
        self._original_cwd = Path.cwd()
        self._temporary = tempfile.TemporaryDirectory()
        self.workdir = Path(self._temporary.name)
        os.chdir(self.workdir)

    def tearDown(self) -> None:
        os.chdir(self._original_cwd)
        self._temporary.cleanup()

    def write_input(self, text: str, name: str = "SPL.txt") -> Path:
        path = self.workdir / name
        path.write_text(text, encoding="ascii")
        return path

    def run_cli(self, argv: list[str] | None = None) -> tuple[int, str, str]:
        """Run main() and capture exit code, stdout, stderr.

        Pass [] to simulate the no-argument case; pass a real list
        to simulate explicit CLI arguments. Passing None is treated
        as [] because unittest owns sys.argv during a test run.
        """
        effective = [] if argv is None else list(argv)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(effective)
        return code, out.getvalue(), err.getvalue()


class CliSuccessTests(CliTestCase):
    def test_default_reads_spl_txt_and_writes_tree_xml(self) -> None:
        self.write_input(MINIMAL_VALID)
        code, out, err = self.run_cli()
        self.assertEqual(code, int(ExitCode.SUCCESS))
        self.assertEqual(out, "")
        self.assertEqual(err, "")
        self.assertTrue((self.workdir / "tree.xml").is_file())

    def test_explicit_input_path_is_used(self) -> None:
        custom = self.write_input(MINIMAL_VALID, name="custom.txt")
        # No SPL.txt exists; CLI must read custom.txt.
        self.assertFalse((self.workdir / "SPL.txt").exists())
        code, _, _ = self.run_cli([str(custom)])
        self.assertEqual(code, int(ExitCode.SUCCESS))
        self.assertTrue((self.workdir / "tree.xml").is_file())

    def test_output_is_well_formed_xml(self) -> None:
        self.write_input(MINIMAL_VALID)
        self.run_cli()
        tree = ET.parse(self.workdir / "tree.xml")
        self.assertEqual(tree.getroot().tag, "syntax_tree")

    def test_input_path_with_spaces_is_supported(self) -> None:
        source = self.write_input(MINIMAL_VALID, name="my SPL input.txt")
        code, _, err = self.run_cli([source.name])
        self.assertEqual(code, int(ExitCode.SUCCESS), err)
        self.assertTrue((self.workdir / "tree.xml").is_file())

    def test_symlink_input_is_supported(self) -> None:
        target = self.write_input(MINIMAL_VALID, name="source.txt")
        link = self.workdir / "linked.txt"
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        code, _, err = self.run_cli([str(link)])
        self.assertEqual(code, int(ExitCode.SUCCESS), err)


class CliUsageTests(CliTestCase):
    def test_too_many_arguments_is_usage_error(self) -> None:
        self.write_input(MINIMAL_VALID)
        code, _, err = self.run_cli(["a.txt", "b.txt"])
        self.assertEqual(code, int(ExitCode.USAGE_ERROR))
        self.assertIn("USAGE-ARGS", err)


class CliInputErrorTests(CliTestCase):
    def test_missing_default_input_reports_input_error(self) -> None:
        # No SPL.txt was created.
        code, _, err = self.run_cli()
        self.assertEqual(code, int(ExitCode.INPUT_ERROR))
        self.assertIn("IO-INPUT-MISSING", err)
        self.assertNotIn("Traceback", err)

    def test_missing_explicit_input_reports_input_error(self) -> None:
        code, _, err = self.run_cli(["does-not-exist.txt"])
        self.assertEqual(code, int(ExitCode.INPUT_ERROR))
        self.assertIn("IO-INPUT-MISSING", err)

    def test_input_and_output_same_file_is_rejected_without_deleting_source(self) -> None:
        source = self.write_input(MINIMAL_VALID, name="tree.xml")
        before = source.read_bytes()
        code, _, err = self.run_cli([str(source)])
        self.assertEqual(code, int(ExitCode.INPUT_ERROR))
        self.assertIn("IO-INPUT-OUTPUT-SAME", err)
        self.assertEqual(source.read_bytes(), before)

    def test_existing_output_directory_reports_clear_error(self) -> None:
        self.write_input(MINIMAL_VALID)
        (self.workdir / "tree.xml").mkdir()
        code, _, err = self.run_cli()
        self.assertEqual(code, int(ExitCode.INTERNAL_ERROR))
        self.assertIn("IO-OUTPUT-CLEAR", err)
        self.assertNotIn("Traceback", err)

    def test_directory_as_input_is_rejected_clearly(self) -> None:
        source = self.workdir / "input-directory"
        source.mkdir()
        code, _, err = self.run_cli([str(source)])
        self.assertEqual(code, int(ExitCode.INPUT_ERROR))
        self.assertIn("IO-INPUT-READ", err)
        self.assertNotIn("Traceback", err)

    def test_broken_input_symlink_is_rejected_clearly(self) -> None:
        source = self.workdir / "broken.txt"
        try:
            source.symlink_to(self.workdir / "missing.txt")
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        code, _, err = self.run_cli([str(source)])
        self.assertEqual(code, int(ExitCode.INPUT_ERROR))
        self.assertIn("IO-INPUT-MISSING", err)

    def test_input_symlink_to_output_is_rejected_without_deleting_target(self) -> None:
        output = self.write_input(MINIMAL_VALID, name="tree.xml")
        link = self.workdir / "linked-source.txt"
        try:
            link.symlink_to(output)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        code, _, err = self.run_cli([str(link)])
        self.assertEqual(code, int(ExitCode.INPUT_ERROR))
        self.assertIn("IO-INPUT-OUTPUT-SAME", err)
        self.assertEqual(output.read_text(encoding="ascii"), MINIMAL_VALID)


class CliSyntaxErrorTests(CliTestCase):
    def test_invalid_syntax_returns_syntax_error(self) -> None:
        # Missing the trailing ':' separator.
        self.write_input(": ")
        code, _, err = self.run_cli()
        self.assertEqual(code, int(ExitCode.SYNTAX_ERROR))
        self.assertIn("syntax[", err)

    def test_invalid_run_removes_xml_from_previous_run(self) -> None:
        # First, a valid run to produce tree.xml.
        self.write_input(MINIMAL_VALID)
        code, _, _ = self.run_cli()
        self.assertEqual(code, int(ExitCode.SUCCESS))
        xml_path = self.workdir / "tree.xml"
        self.assertTrue(xml_path.is_file())

        # Then, an invalid run in the same directory.
        self.write_input(": ")
        code, _, _ = self.run_cli()
        self.assertEqual(code, int(ExitCode.SYNTAX_ERROR))

        # A failed compilation cannot leave the previous result looking current.
        self.assertFalse(xml_path.exists())

    def test_missing_input_removes_xml_from_previous_run(self) -> None:
        self.write_input(MINIMAL_VALID)
        code, _, _ = self.run_cli()
        self.assertEqual(code, int(ExitCode.SUCCESS))
        xml_path = self.workdir / "tree.xml"
        self.assertTrue(xml_path.is_file())

        (self.workdir / "SPL.txt").unlink()
        code, _, _ = self.run_cli()
        self.assertEqual(code, int(ExitCode.INPUT_ERROR))
        self.assertFalse(xml_path.exists())


class CliLexicalErrorTests(CliTestCase):
    def test_final_token_without_blank_space_is_rejected(self) -> None:
        self.write_input(": :")
        code, _, err = self.run_cli()
        self.assertEqual(code, int(ExitCode.LEXICAL_ERROR))
        self.assertIn("LEX-NO-SEPARATOR", err)
        self.assertFalse((self.workdir / "tree.xml").exists())

    def test_non_ascii_input_is_rejected(self) -> None:
        (self.workdir / "SPL.txt").write_bytes(b": caf\xe9 : ")
        code, _, err = self.run_cli()
        self.assertIn(
            code,
            (int(ExitCode.INPUT_ERROR), int(ExitCode.LEXICAL_ERROR)),
        )
        self.assertNotIn("Traceback", err)

    def test_non_ascii_run_removes_xml_from_previous_run(self) -> None:
        self.write_input(MINIMAL_VALID)
        self.assertEqual(self.run_cli()[0], int(ExitCode.SUCCESS))
        xml_path = self.workdir / "tree.xml"
        self.assertTrue(xml_path.is_file())
        (self.workdir / "SPL.txt").write_bytes(b": caf\xe9 : ")
        self.assertNotEqual(self.run_cli()[0], int(ExitCode.SUCCESS))
        self.assertFalse(xml_path.exists())

    def test_utf8_bom_is_rejected(self) -> None:
        (self.workdir / "SPL.txt").write_bytes(b"\xef\xbb\xbf: : ")
        code, _, err = self.run_cli()
        self.assertEqual(code, int(ExitCode.LEXICAL_ERROR))
        self.assertIn("LEX-NON-ASCII", err)
        self.assertFalse((self.workdir / "tree.xml").exists())

    def test_ascii_nul_is_rejected(self) -> None:
        (self.workdir / "SPL.txt").write_bytes(b": \x00 : ")
        code, _, err = self.run_cli()
        self.assertEqual(code, int(ExitCode.LEXICAL_ERROR))
        self.assertIn("LEX-UNKNOWN", err)
        self.assertFalse((self.workdir / "tree.xml").exists())


if __name__ == "__main__":
    unittest.main()
