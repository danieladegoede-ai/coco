"""Command-line entry point for the SPL front end."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from spl_frontend.cli_contract import CliRequest
from spl_frontend.compiler import compile_file
from spl_frontend.diagnostics import (
    Diagnostic,
    DiagnosticPhase,
    ExitCode,
    FrontendError,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, run the compiler, return exit code."""
    args = list(sys.argv[1:] if argv is None else argv)

    if len(args) > 1:
        _print_usage_error(len(args))
        return int(ExitCode.USAGE_ERROR)

    default = CliRequest()
    input_path = Path(args[0]) if args else default.input_path
    output_path = default.output_path

    try:
        compile_file(input_path, output_path)
    except FrontendError as exc:
        print(exc.diagnostic.render(), file=sys.stderr)
        return int(exc.exit_code)
    except Exception as exc:
        print(
            f"internal[INT-UNEXPECTED]: unexpected failure: {exc}",
            file=sys.stderr,
        )
        return int(ExitCode.INTERNAL_ERROR)

    return int(ExitCode.SUCCESS)


def _print_usage_error(count: int) -> None:
    diagnostic = Diagnostic(
        phase=DiagnosticPhase.DRIVER,
        code="USAGE-ARGS",
        message=f"expected at most one input path, got {count}",
        path=Path("."),
        line=1,
        column=1,
        hint="usage: python -m spl_frontend [input.txt]",
    )
    print(diagnostic.render(), file=sys.stderr)