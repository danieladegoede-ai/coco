"""Shared helpers for target code-generation compile-and-run tests."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from spl_frontend.codegen import CallEmitter, generate_target
from spl_frontend.target_writer import render_target
from spl_frontend.lexer import tokenize
from spl_frontend.name_analysis import resolve_names
from spl_frontend.parser import parse
from spl_frontend.semantic_model import CheckedProgram
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.type_analysis import check_types


TARGET_CXX = shutil.which("g++") or shutil.which("clang++")


def checked_source(source: str, path: Path | None = None) -> CheckedProgram:
    if not source or not source[-1].isspace():
        raise ValueError("Every test SPL source must end with a blank-space separator.")
    source_path = path or Path("codegen-test.spl")
    tree = SyntaxTree()
    parse(tokenize(SourceFile(source_path, source)), tree, source_path)
    tree.validate()
    resolved = resolve_names(tree, path=source_path)
    return check_types(resolved)


def target_source(source: str, call_emitter: CallEmitter | None = None) -> tuple[CheckedProgram, str]:
    checked = checked_source(source)
    return checked, render_target(generate_target(checked, call_emitter=call_emitter))


def compile_and_run_target(
    target: str,
    *,
    timeout: float = 5.0,
    compiler: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str]]:
    executable_compiler = compiler or TARGET_CXX
    if executable_compiler is None:
        raise RuntimeError("No C++ compiler found (looked for g++ and clang++).")
    with tempfile.TemporaryDirectory(prefix="spl-codegen-test-") as temp_dir:
        root = Path(temp_dir)
        target_path = root / "program.cpp"
        executable_path = root / "program"
        target_path.write_text(target, encoding="utf-8")
        compilation = subprocess.run(
            [executable_compiler, "-std=c++17", "-Wall", "-Wextra", "-pedantic", str(target_path), "-o", str(executable_path)],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if compilation.returncode != 0:
            raise AssertionError(
                "Generated target failed to compile.\n"
                f"Command: {executable_compiler} -std=c++17 {target_path} -o {executable_path}\n"
                f"stdout:\n{compilation.stdout}\nstderr:\n{compilation.stderr}\nTarget:\n{target}"
            )
        execution = subprocess.run(
            [str(executable_path)],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return compilation, execution


def run_source(
    source: str,
    expected_stdout: str,
    *,
    call_emitter: CallEmitter | None = None,
    timeout: float = 5.0,
) -> str:
    checked, generated = target_source(source, call_emitter)
    compilation, execution = compile_and_run_target(generated, timeout=timeout)
    if execution.returncode != 0:
        raise AssertionError(
            f"Generated executable exited {execution.returncode}; stderr={execution.stderr!r}\n{generated}"
        )
    if execution.stdout != expected_stdout:
        raise AssertionError(
            f"Wrong executable output: expected {expected_stdout!r}, got {execution.stdout!r}.\n"
            f"Generated target:\n{generated}\nTarget compiler stderr:\n{compilation.stderr}"
        )
    return generated
