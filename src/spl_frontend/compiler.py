"""Frontend-only compatibility API and the complete checked SPL compiler."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import os
import tempfile

from spl_frontend.cli_contract import DEFAULT_OUTPUT_PATH, DEFAULT_TARGET_PATH
from spl_frontend.name_analysis import resolve_names
from spl_frontend.semantic_model import CheckedProgram
from spl_frontend.semantic_model import FoundationError
from spl_frontend.source_map import SourceMap, build_source_map
from spl_frontend.type_analysis import TypeAnalysisError, check_types

from spl_frontend.diagnostics import (
    Diagnostic,
    DiagnosticPhase,
    ExitCode,
    FrontendError,
)
from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import load_source
from spl_frontend.tree import SyntaxTree
from spl_frontend.xml_writer import write_tree


def compile_file(input_path: Path, output_path: Path) -> None:
    """Compile one input, removing the previous result before this attempt.

    The XML writer protects atomic replacement after parsing. This driver
    removes stale output before reading, so an earlier successful compilation
    cannot be mistaken for the result of a later failed one.
    """
    if _aliases(input_path, output_path):
        raise _frontend_error(
            ExitCode.INPUT_ERROR,
            DiagnosticPhase.DRIVER,
            "IO-INPUT-OUTPUT-SAME",
            "input and output paths refer to the same file",
            input_path,
            hint="choose a source path other than tree.xml",
        )
    try:
        output_path.unlink(missing_ok=True)
    except OSError as exc:
        raise _frontend_error(
            ExitCode.INTERNAL_ERROR,
            DiagnosticPhase.DRIVER,
            "IO-OUTPUT-CLEAR",
            f"cannot remove previous output: {exc}",
            output_path,
        ) from exc

    try:
        source = load_source(input_path)
    except FileNotFoundError as exc:
        raise _frontend_error(
            ExitCode.INPUT_ERROR,
            DiagnosticPhase.DRIVER,
            "IO-INPUT-MISSING",
            f"input file not found: {input_path}",
            input_path,
            hint="check that SPL.txt exists in the current directory",
        ) from exc
    except OSError as exc:
        raise _frontend_error(
            ExitCode.INPUT_ERROR,
            DiagnosticPhase.DRIVER,
            "IO-INPUT-READ",
            f"cannot read input file: {exc}",
            input_path,
        ) from exc

    tokens = tokenize(source)
    tree = SyntaxTree()
    parse(tokens, tree, input_path)
    tree.validate()
    write_tree(tree, output_path)


@dataclass(frozen=True, slots=True)
class CompilationResult:
    """Successful in-memory result; no target compiler is needed to obtain it."""

    checked: CheckedProgram
    target_source: str


def compile_tree(
    tree: SyntaxTree, source_map: SourceMap | None = None, *, path: Path | None = None,
) -> CompilationResult:
    """Compile parser output or validated imported XML without publishing files.

    XML-only callers supply path=xml_path and receive node-ID semantic errors.
    Original source tokens, when available, provide exact source diagnostics.
    """
    from spl_frontend.inlining import generate_program
    from spl_frontend.codegen_ir import CodegenError
    from spl_frontend.target_writer import render_target

    resolved = resolve_names(tree, source_map, path=path)
    try:
        checked = check_types(resolved)
        program = generate_program(checked)
        return CompilationResult(checked, render_target(program))
    except (TypeAnalysisError, CodegenError, FoundationError) as exc:
        # XML-only semantic snapshots have node IDs but no span/path field.
        # Retain the caller's known file without inventing source coordinates.
        if exc.path is None:
            exc.path = source_map.path if source_map is not None else path
        raise


def compile_program(
    input_path: Path, target_path: Path = DEFAULT_TARGET_PATH,
    *, xml_path: Path = DEFAULT_OUTPUT_PATH,
) -> CompilationResult:
    """Run all passes, then publish fresh XML/target source atomically per file.

    Protect inputs (including hard links) before output invalidation. A failed
    attempt clears both outputs; publication failure also rolls back this run's
    XML/target. The frontend-only compile_file contract remains available.
    """
    outputs = (target_path, xml_path)
    if any(_aliases(input_path, output) for output in outputs):
        raise _frontend_error(
            ExitCode.INPUT_ERROR, DiagnosticPhase.DRIVER, "IO-INPUT-OUTPUT-SAME",
            "input and output paths refer to the same file", input_path,
            hint="choose a source path other than tree.xml or program.cpp",
        )
    if _aliases(target_path, xml_path):
        raise _frontend_error(
            ExitCode.INPUT_ERROR, DiagnosticPhase.DRIVER, "IO-OUTPUT-ALIAS",
            "XML and target outputs must be different files", input_path,
        )
    failures = []
    for output in outputs:
        try:
            output.unlink(missing_ok=True)
        except OSError as exc:
            failures.append((output, exc))
    if failures:
        output, exc = failures[0]
        raise _frontend_error(
            ExitCode.INTERNAL_ERROR, DiagnosticPhase.DRIVER, "IO-OUTPUT-CLEAR",
            f"cannot remove previous output: {exc}", output,
        ) from exc
    try:
        source = load_source(input_path)
    except FileNotFoundError as exc:
        raise _frontend_error(
            ExitCode.INPUT_ERROR, DiagnosticPhase.DRIVER, "IO-INPUT-MISSING",
            f"input file not found: {input_path}", input_path,
            hint="check that SPL.txt exists in the current directory",
        ) from exc
    except OSError as exc:
        raise _frontend_error(
            ExitCode.INPUT_ERROR, DiagnosticPhase.DRIVER, "IO-INPUT-READ",
            f"cannot read input file: {exc}", input_path,
        ) from exc
    tokens = tokenize(source)
    tree = parse(tokens, SyntaxTree(), input_path)
    locations = build_source_map(tree, tokens, input_path)
    result = compile_tree(tree, locations)
    try:
        write_tree(tree, xml_path)
        _write_target(result.target_source, target_path)
    except Exception:
        for output in outputs:
            try:
                output.unlink(missing_ok=True)
            except OSError:
                pass  # Preserve the original actionable publication failure.
        raise
    return result


def _aliases(first: Path, second: Path) -> bool:
    if first.resolve() == second.resolve():
        return True
    try:
        return first.samefile(second)
    except (FileNotFoundError, OSError):
        return False


def _write_target(source: str, output: Path) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(source)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    except OSError as exc:
        raise _frontend_error(
            ExitCode.GENERATION_ERROR, DiagnosticPhase.GENERATION, "GEN-WRITE",
            f"cannot publish target source: {exc}", output,
        ) from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass  # Keep the original publication failure actionable.


def _frontend_error(
    code: ExitCode,
    phase: DiagnosticPhase,
    diag_code: str,
    message: str,
    path: Path,
    line: int = 1,
    column: int = 1,
    hint: str | None = None,
) -> FrontendError:
    return FrontendError(
        code,
        Diagnostic(phase, diag_code, message, path, line, column, hint),
    )
