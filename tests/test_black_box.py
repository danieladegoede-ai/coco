"""Tests for the subprocess black-box harness itself."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.black_box_test import build_command, build_env, run_repeated_sequence


class BlackBoxHarnessTests(unittest.TestCase):
    def test_relative_executable_path_is_resolved_before_temp_directory_run(self) -> None:
        self.assertEqual(build_command("group-2.exe"), [str(Path("group-2.exe").resolve())])

    def test_valid_invalid_valid_sequence_has_no_stale_output(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertIsNone(run_repeated_sequence(executable=None, env=build_env(root)))


if __name__ == "__main__":
    unittest.main()
