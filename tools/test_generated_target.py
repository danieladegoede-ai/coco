"""Source-based backend acceptance runner with separate compile/run evidence.

The default subprocess adapter exercises the checked-program/codegen API. It
does not claim final CLI/inliner or native-package integration. Supply an
external compiler command for those downstream checks. Each failing case keeps
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


def _run(command: list[str], cwd: Path, timeout: float) -> tuple[int | str, str, str]:
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
    # This adapter is deliberately confined to Cherise's existing API. It
    # preserves the inliner hook boundary and rejects calls without an inliner.
    sys.path.insert(0, str(ROOT / "src"))
    from spl_frontend.codegen import generate_target
    from spl_frontend.diagnostics import FrontendError
    from spl_frontend.lexer import tokenize
    from spl_frontend.name_analysis import resolve_names
    from spl_frontend.parser import parse
    from spl_frontend.source import SourceFile
    from spl_frontend.source_map import build_source_map
    from spl_frontend.target_writer import write_target
    from spl_frontend.tree import SyntaxTree
    from spl_frontend.type_analysis import check_types

    try:
        source = SourceFile(input_path, input_path.read_text(encoding="utf-8"))
        tokens = tokenize(source)
        tree = SyntaxTree()
        parse(tokens, tree, input_path)
        resolved = resolve_names(tree, build_source_map(tree, tokens, input_path))
        write_target(generate_target(check_types(resolved)), target_path)
    except FrontendError as exc:
        print(exc.diagnostic.render(), file=sys.stderr)
        return int(exc.exit_code)
    except Exception as exc:
        # A failed subprocess is evidence, including unexpected tracebacks.
        # Expected library diagnostics remain traceback-free.
        if hasattr(exc, "render"):
            print(exc.render(), file=sys.stderr)
            return 1
        raise
    return 0


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
    runtime_limit = timeout if execution_timeout is None else execution_timeout
    report = CaseReport(case_id=case_id, seed=seed)
    cxx = target_compiler or shutil.which("c++") or shutil.which("g++") or "c++"
    with tempfile.TemporaryDirectory(prefix="spl-target-case-") as temporary:
        work = Path(temporary)
        input_path = work / "SPL.txt"
        target_path = work / "program.cpp"
        executable = work / "program"
        input_path.write_text(source, encoding="utf-8")
        logs: dict[str, str] = {}

        def stage(name: str, command: list[str], limit: float) -> tuple[int | str, str, str]:
            report.commands[name] = command
            status, stdout, stderr = _run(command, work, limit)
            logs[name + ".stdout.log"] = stdout
            logs[name + ".stderr.log"] = stderr
            return status, stdout, stderr

        if pre_generated_target is not None:
            target_path.write_text(pre_generated_target, encoding="utf-8")
        else:
            command = (
                [item.replace("{input}", str(input_path)).replace("{target}", str(target_path)) for item in compiler_command]
                if compiler_command is not None else
                [sys.executable, str(Path(__file__).resolve()), "--compile-source", str(input_path), str(target_path)]
            )
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
            report.target_compile_status, _, _ = stage("target-compile", command, timeout)
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
            if target_path.exists():
                shutil.copyfile(target_path, saved / "program.cpp")
            for name, contents in logs.items():
                (saved / name).write_text(contents, encoding="utf-8")
            metadata = {
                "case_id": case_id, "seed": seed, "commands": report.commands,
                "timeout": timeout, "execution_timeout": runtime_limit,
                "python": sys.version, "platform": sys.platform,
                "compiler_adapter": "checked-program API" if compiler_command is None else "external command",
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
            report.artifact_dir = str(saved)
            report.reproduction_command = "sh reproduce.sh"
            (saved / "report.json").write_text(json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8")
    return report


def run_manifest(
    manifest: Path, *, artifacts: Path | None = None, target_compiler: str | None = None,
    timeout: float = 5.0, seed: int | None = None, compiler_command: Sequence[str] | None = None,
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
    compiler_command = json.loads(args.compiler_command) if args.compiler_command is not None else None
    if compiler_command is not None and (
        not isinstance(compiler_command, list) or not compiler_command or
        any(not isinstance(item, str) for item in compiler_command)
    ):
        parser.error("--compiler-command must be a nonempty JSON argv array")
    options = dict(artifacts=args.artifacts, target_compiler=args.target_compiler,
                   timeout=args.timeout, seed=args.seed, compiler_command=compiler_command)
    if args.manifest:
        reports, summary = run_manifest(args.manifest, **options)
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
