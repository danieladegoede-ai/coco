"""Black-box test harness for the SPL front end.

Runs the CLI as a subprocess the same way the tutors will run the
packaged executable. Verifies exit codes, stderr, and the output XML
file lifecycle in fresh temporary directories.

The harness is designed to work in two modes:

- Development: runs `python -m spl_frontend` with PYTHONPATH=src.
- Packaged: runs a native executable (set `executable` to its path).

Failure reports are written to a report directory so failed cases can be
inspected after the run.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


MINIMAL_VALID = ": : "


@dataclass(slots=True)
class Case:
    """One black-box test case."""

    name: str
    input_text: str
    expect_success: bool
    expected_exit_code: int | None = None


@dataclass(slots=True)
class Result:
    """Result of running one case."""

    case: Case
    exit_code: int
    stdout: str
    stderr: str
    xml_exists: bool
    xml_valid: bool
    failure_reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.failure_reason is None


def default_cases() -> list[Case]:
    """Return a small handwritten suite covering key scenarios."""
    return [
        Case("minimal_valid", MINIMAL_VALID, expect_success=True),
        Case("missing_second_colon", ": ", expect_success=False),
        Case("missing_semicolon", ": : nop", expect_success=False),
        Case("empty_input", "", expect_success=False),
        Case("trailing_junk", MINIMAL_VALID + "garbage ", expect_success=False),
        Case("uppercase_name", ": : #A = 0 ; ", expect_success=False),
        Case("unknown_symbol", ": : @ ", expect_success=False),
        Case("non_ascii", ": caf\u00e9 : ", expect_success=False),
        Case("missing_final_blank_space", ": :", expect_success=False,
             expected_exit_code=4),
    ]


def build_command(executable: str | None) -> list[str]:
    """Return the command that the harness should run."""
    if executable:
        return [str(Path(executable).resolve())]
    return [sys.executable, "-m", "spl_frontend"]


def build_env(repo_root: Path) -> dict[str, str]:
    """Return an environment with PYTHONPATH pointing at src/."""
    env = dict(os.environ)
    src = repo_root / "src"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}" if existing else str(src)
    return env


def run_case(
    case: Case,
    *,
    executable: str | None,
    env: dict[str, str],
) -> Result:
    """Run one case in a fresh temporary directory."""
    with tempfile.TemporaryDirectory() as directory:
        workdir = Path(directory)
        (workdir / "SPL.txt").write_bytes(case.input_text.encode("utf-8"))

        command = build_command(executable)
        try:
            completed = subprocess.run(
                command,
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return Result(
                case=case,
                exit_code=-1,
                stdout="",
                stderr="",
                xml_exists=False,
                xml_valid=False,
                failure_reason="timed out after 30s",
            )
        except OSError as exc:
            return Result(
                case=case,
                exit_code=-1,
                stdout="",
                stderr="",
                xml_exists=False,
                xml_valid=False,
                failure_reason=f"could not start command: {exc}",
            )

        xml_path = workdir / "tree.xml"
        xml_exists = xml_path.exists()
        xml_valid = False
        if xml_exists:
            try:
                ET.parse(xml_path)
                xml_valid = True
            except ET.ParseError:
                xml_valid = False

        reason = _check(case, completed, xml_exists, xml_valid)
        return Result(
            case=case,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            xml_exists=xml_exists,
            xml_valid=xml_valid,
            failure_reason=reason,
        )


def _check(
    case: Case,
    completed: subprocess.CompletedProcess[str],
    xml_exists: bool,
    xml_valid: bool,
) -> str | None:
    """Return None if the case passed, otherwise a description of the failure."""
    if case.expect_success:
        if completed.returncode != 0:
            return (
                f"expected exit 0, got {completed.returncode}; "
                f"stderr={completed.stderr.strip()!r}"
            )
        if not xml_exists:
            return "expected tree.xml to exist after a successful run"
        if not xml_valid:
            return "tree.xml is not well-formed XML"
        return None

    # Failure case
    if completed.returncode == 0:
        return "expected non-zero exit code, got 0"
    if case.expected_exit_code is not None:
        if completed.returncode != case.expected_exit_code:
            return (
                f"expected exit {case.expected_exit_code}, "
                f"got {completed.returncode}"
            )
    if xml_exists:
        return "tree.xml was published on a failure case"
    if "Traceback" in completed.stderr:
        return "diagnostic contained a Python traceback"
    return None


def run_suite(
    cases: list[Case],
    *,
    executable: str | None = None,
    report_dir: Path | None = None,
) -> tuple[int, int]:
    """Run all cases. Return (passed, total)."""
    repo_root = Path(__file__).resolve().parents[1]
    env = build_env(repo_root)

    passed = 0
    for case in cases:
        result = run_case(case, executable=executable, env=env)
        if result.passed:
            passed += 1
            print(f"PASS  {case.name}")
        else:
            print(f"FAIL  {case.name}: {result.failure_reason}")
            if report_dir is not None:
                report_dir.mkdir(parents=True, exist_ok=True)
                report = report_dir / f"{case.name}.txt"
                report.write_text(
                    _format_report(result),
                    encoding="utf-8",
                )
                print(f"      report: {report}")

    return passed, len(cases)


def run_repeated_sequence(*, executable: str | None, env: dict[str, str]) -> str | None:
    """Check valid, invalid, then valid runs in one working directory."""
    command = build_command(executable)
    with tempfile.TemporaryDirectory() as directory:
        workdir = Path(directory)
        source = workdir / "SPL.txt"
        output = workdir / "tree.xml"
        for text, expect_success in ((": : ", True), (": ", False), (": : ", True)):
            source.write_text(text, encoding="ascii")
            try:
                completed = subprocess.run(
                    command, cwd=workdir, env=env, capture_output=True,
                    text=True, timeout=30,
                )
            except subprocess.TimeoutExpired:
                return "timed out after 30s"
            except OSError as exc:
                return f"could not start command: {exc}"
            if expect_success:
                if completed.returncode != 0 or not output.is_file():
                    return f"valid run failed: exit {completed.returncode}; {completed.stderr.strip()}"
                try:
                    if ET.parse(output).getroot().tag != "syntax_tree":
                        return "valid run produced an unexpected XML root"
                except ET.ParseError:
                    return "valid run produced malformed XML"
            elif completed.returncode == 0 or output.exists():
                return "invalid run succeeded or left stale tree.xml"
    return None


def _format_report(result: Result) -> str:
    lines = [
        f"Case: {result.case.name}",
        f"Input: {result.case.input_text!r}",
        f"Expect success: {result.case.expect_success}",
        f"Exit code: {result.exit_code}",
        f"tree.xml exists: {result.xml_exists}",
        f"tree.xml valid: {result.xml_valid}",
        f"Failure: {result.failure_reason}",
        "",
        "stdout:",
        result.stdout,
        "",
        "stderr:",
        result.stderr,
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run black-box tests against the SPL front end.",
    )
    parser.add_argument(
        "--executable",
        help="Path to a packaged executable. If omitted, runs "
             "`python -m spl_frontend`.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("scratch") / "black-box-reports",
        help="Directory to write failure reports to.",
    )
    args = parser.parse_args(argv)

    passed, total = run_suite(
        default_cases(),
        executable=args.executable,
        report_dir=args.report_dir,
    )
    sequence_failure = run_repeated_sequence(
        executable=args.executable,
        env=build_env(Path(__file__).resolve().parents[1]),
    )
    total += 1
    if sequence_failure is None:
        passed += 1
        print("PASS  valid_invalid_valid_sequence")
    else:
        print(f"FAIL  valid_invalid_valid_sequence: {sequence_failure}")
    print(f"\n{passed}/{total} cases passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
