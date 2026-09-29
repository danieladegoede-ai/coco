"""Coordinate the SPL front-end pipeline: read, tokenize, parse, validate, write."""

from __future__ import annotations

from pathlib import Path

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
    if input_path.resolve() == output_path.resolve():
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
