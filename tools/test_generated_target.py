"""Source-based backend acceptance runner with separate compile/run evidence.

The default subprocess adapter exercises the full public compiler CLI.
An external command reruns the same corpus against a packaged compiler; no
package is built by this tool. Each failing case keeps
its source, target, expectations, commands, stage logs and a bounded replay.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.target_inspector import inspect_target


@dataclass(slots=True)
class CaseReport:
    case_id: str
    seed: int | None = None
    passed: bool = False
    failure_stage: str | None = None
    compiler_status: int | str = "not-run"
    compiler_stdout: str = ""
    compiler_stderr: str = ""
    target_structure_status: str = "not-run"
    target_issues: list[dict] = field(default_factory=list)
    target_compile_status: int | str | None = None
    target_compile_stdout: str = ""
    target_compile_stderr: str = ""
    execution_status: int | str | None = None
    stdout_matches: bool | None = None
    stdout: str = ""
    stderr: str = ""
    commands: dict[str, list[str]] = field(default_factory=dict)
    artifact_dir: str | None = None
    reproduction_command: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def run_process(command: list[str], cwd: Path, timeout: float) -> tuple[int | str, str, str]:
    try:
        result = subprocess.run(
            command, cwd=cwd, text=True, encoding="utf-8", errors="replace",
            capture_output=True, check=False, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return "timeout", _text(exc.stdout), _text(exc.stderr) + f"\nTimed out after {timeout:g} seconds.\n"
    except OSError as exc:
        return "unavailable", "", str(exc) + "\n"


def _compile_source(input_path: Path, target_path: Path) -> int:
    # The subprocess enters the actual public command from its fresh cwd.
    sys.path.insert(0, str(ROOT / "src"))
    from spl_frontend.cli import main
    from spl_frontend.cli_contract import DEFAULT_TARGET_PATH
    if target_path.resolve() != DEFAULT_TARGET_PATH.resolve():
        raise ValueError("The CLI adapter expects its default target path.")
    return main([str(input_path)])


def normalize_compiler_command(external: Sequence[str] | None) -> list[str] | None:
    """Freeze an existing relative executable path before temporary cwd/replay."""
    if external is None:
        return None
    if isinstance(external, str) or not external or any(not isinstance(item, str) for item in external):
        raise ValueError("Compiler command must be a nonempty argv sequence.")
    command = list(external)
    if Path(command[0]).is_file():
        command[0] = str(Path(command[0]).resolve())
    return command


def compiler_command_for(input_path: Path, target_path: Path,
                         external: Sequence[str] | None = None) -> list[str]:
    """Build argv without a shell; preserve input/target placeholder support."""
    command = normalize_compiler_command(external)
    if command is None:
        return [sys.executable, str(Path(__file__).resolve()), "--compile-source",
                str(input_path), str(target_path)]
    return [item.replace("{input}", str(input_path)).replace("{target}", str(target_path))
            for item in command]


def verify_case(
    source: str,
    expected_stdout: str,
    *,
    case_id: str = "case",
    target_compiler: str | None = None,
    compiler_command: Sequence[str] | None = None,
    timeout: float = 5.0,
    execution_timeout: float | None = None,
    artifacts: Path | None = None,
    pre_generated_target: str | None = None,
    seed: int | None = None,
) -> CaseReport:
    """Verify one exact-output case; retain evidence on every failed stage.

    An external compiler runs in a fresh directory containing SPL.txt and must
    write program.cpp there. Optional {input}/{target} placeholders expand to
    absolute paths without a shell. Pre-generated targets bypass that stage.
    """
    if timeout <= 0 or (execution_timeout is not None and execution_timeout <= 0):
        raise ValueError("Timeouts must be positive.")
    compiler_command = normalize_compiler_command(compiler_command)
    runtime_limit = timeout if execution_timeout is None else execution_timeout
    report = CaseReport(case_id=case_id, seed=seed)
    cxx = target_compiler or shutil.which("c++") or shutil.which("g++") or "c++"
    if Path(cxx).is_file():
        cxx = str(Path(cxx).resolve())
    with tempfile.TemporaryDirectory(prefix="spl-target-case-") as temporary:
        work = Path(temporary)
        input_path = work / "SPL.txt"
        target_path = work / "program.cpp"
        executable = work / "program"
        input_path.write_text(source, encoding="utf-8")
        logs: dict[str, str] = {}

        def stage(name: str, command: list[str], limit: float) -> tuple[int | str, str, str]:
            report.commands[name] = command
            status, stdout, stderr = run_process(command, work, limit)
            logs[name + ".stdout.log"] = stdout
            logs[name + ".stderr.log"] = stderr
            return status, stdout, stderr

        if pre_generated_target is not None:
            target_path.write_text(pre_generated_target, encoding="utf-8")
        else:
            command = compiler_command_for(input_path, target_path, compiler_command)
            report.compiler_status, report.compiler_stdout, report.compiler_stderr = stage("compiler", command, timeout)
            if report.compiler_status != 0:
                report.failure_stage = "compiler-timeout" if report.compiler_status == "timeout" else "compiler-process"
            elif not target_path.is_file():
                report.failure_stage = "compiler-output-missing"

        if report.failure_stage is None:
            try:
                target = target_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                report.failure_stage = "compiler-output-invalid"
                logs["compiler-output.stderr.log"] = str(exc) + "\n"
            else:
                report.target_issues = [asdict(item) for item in inspect_target(target)]
                report.target_structure_status = "failed" if report.target_issues else "passed"
                if report.target_issues:
                    report.failure_stage = "target-structure"

        if report.failure_stage is None:
            command = [cxx, "-std=c++17", "-Wall", "-Wextra", "-pedantic", str(target_path), "-o", str(executable)]
            report.target_compile_status, report.target_compile_stdout, report.target_compile_stderr = stage("target-compile", command, timeout)
            if report.target_compile_status != 0:
                report.failure_stage = "target-compile-timeout" if report.target_compile_status == "timeout" else "target-compilation"

        if report.failure_stage is None:
            report.execution_status, report.stdout, report.stderr = stage("target-run", [str(executable)], runtime_limit)
            if report.execution_status == "timeout":
                report.failure_stage = "target-timeout"
            elif report.execution_status != 0:
                report.failure_stage = "target-execution"
            else:
                report.stdout_matches = report.stdout == expected_stdout
                if not report.stdout_matches:
                    report.failure_stage = "output-mismatch"
        report.passed = report.failure_stage is None

        if not report.passed:
            artifact_root = Path(artifacts) if artifacts is not None else ROOT / "build" / "target-failures"
            artifact_root.mkdir(parents=True, exist_ok=True)
            safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", case_id)[:100] or "case"
            saved = Path(tempfile.mkdtemp(prefix=safe_id + "-", dir=artifact_root)).resolve()
            (saved / "input.spl").write_text(source, encoding="utf-8")
            (saved / "expected.stdout").write_text(expected_stdout, encoding="utf-8")
            if target_path.is_file():
                shutil.copyfile(target_path, saved / "program.cpp")
            for name, contents in logs.items():
                (saved / name).write_text(contents, encoding="utf-8")
            metadata = {
                "case_id": case_id, "seed": seed, "commands": report.commands,
                "timeout": timeout, "execution_timeout": runtime_limit,
                "python": sys.version, "platform": sys.platform,
                "compiler_adapter": "pre-generated target" if pre_generated_target is not None else "full compiler CLI" if compiler_command is None else "external command",
            }
            (saved / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            replay = [
                sys.executable, str(Path(__file__).resolve()), "--source", "input.spl",
                "--expected", "expected.stdout", "--case-id", case_id,
                "--target-compiler", cxx, "--timeout", str(timeout),
                "--execution-timeout", str(runtime_limit), "--artifacts", "replay-artifacts",
            ]
            if pre_generated_target is not None:
                replay += ["--target", "program.cpp"]
            elif compiler_command is not None:
                replay += ["--compiler-command", json.dumps(list(compiler_command))]
            if seed is not None:
                replay += ["--seed", str(seed)]
            (saved / "reproduce.sh").write_text(
                '#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\nexec ' + shlex.join(replay) + "\n",
                encoding="utf-8",
            )
            (saved / "replay.json").write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
            (saved / "reproduce.py").write_text(
                "import json, pathlib, subprocess\n"
                "p = pathlib.Path(__file__).resolve().parent\n"
                "raise SystemExit(subprocess.run(json.loads((p/'replay.json').read_text()), cwd=p).returncode)\n",
                encoding="utf-8",
            )
            report.artifact_dir = str(saved)
            report.reproduction_command = "sh reproduce.sh"
            (saved / "report.json").write_text(json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8")
    return report


def run_manifest(
    manifest: Path, *, artifacts: Path | None = None, target_compiler: str | None = None,
    timeout: float = 5.0, seed: int | None = None, compiler_command: Sequence[str] | None = None,
    execution_timeout: float | None = None,
) -> tuple[list[CaseReport], dict]:
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    reports: list[CaseReport] = []
    blocked: list[str] = []
    for case in data["cases"]:
        if case.get("blocked"):
            blocked.append(case["id"])
            continue
        reports.append(verify_case(
            case["source"], case["expected_stdout"], case_id=case["id"], artifacts=artifacts,
            target_compiler=target_compiler, timeout=timeout, seed=seed, compiler_command=compiler_command,
            execution_timeout=execution_timeout,
        ))
    return reports, {
        "runnable": len(reports), "passed": sum(report.passed for report in reports),
        "failed": sum(not report.passed for report in reports), "blocked": blocked,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile-source", nargs=2, metavar=("INPUT", "TARGET"), help=argparse.SUPPRESS)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--target", type=Path, help="Use saved target, bypassing compiler process")
    parser.add_argument("--case-id", default="case")
    parser.add_argument("--target-compiler")
    parser.add_argument("--compiler-command", help="JSON argv array; runs without a shell")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--execution-timeout", type=float)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    if args.compile_source:
        return _compile_source(*(Path(path) for path in args.compile_source))
    try:
        compiler_command = json.loads(args.compiler_command) if args.compiler_command is not None else None
    except json.JSONDecodeError as exc:
        parser.error(f"Invalid --compiler-command JSON: {exc}")
    if args.timeout <= 0 or (args.execution_timeout is not None and args.execution_timeout <= 0):
        parser.error("Timeouts must be positive")
    if compiler_command is not None and (
        not isinstance(compiler_command, list) or not compiler_command or
        any(not isinstance(item, str) for item in compiler_command)
    ):
        parser.error("--compiler-command must be a nonempty JSON argv array")
    options = dict(artifacts=args.artifacts, target_compiler=args.target_compiler,
                   timeout=args.timeout, seed=args.seed, compiler_command=compiler_command)
    if args.manifest:
        reports, summary = run_manifest(args.manifest, execution_timeout=args.execution_timeout, **options)
        print(json.dumps({"summary": summary, "reports": [report.to_json() for report in reports]}, indent=2))
        return int(bool(summary["failed"] or summary["blocked"]))
    if args.source is None or args.expected is None:
        parser.error("supply --manifest or both --source and --expected")
    report = verify_case(
        args.source.read_text(encoding="utf-8"), args.expected.read_text(encoding="utf-8"),
        case_id=args.case_id, execution_timeout=args.execution_timeout,
        pre_generated_target=args.target.read_text(encoding="utf-8") if args.target else None, **options,
    )
    print(json.dumps(report.to_json(), indent=2))
    return int(not report.passed)


if __name__ == "__main__":
    raise SystemExit(main())
