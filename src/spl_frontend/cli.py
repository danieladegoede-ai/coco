"""Full compiler command, with an explicit frontend-only regression mode."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from spl_frontend.cli_contract import CliRequest
from spl_frontend.compiler import compile_file, compile_program
from spl_frontend.name_analysis import NameAnalysisError
from spl_frontend.type_analysis import TypeAnalysisError
from spl_frontend.numeric_policy import NumericPolicyError
from spl_frontend.semantic_model import FoundationError
from spl_frontend.codegen_ir import CodegenError
from spl_frontend.diagnostics import (
    Diagnostic,
    DiagnosticPhase,
    ExitCode,
    FrontendError,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, run the compiler, return exit code."""
    args = list(sys.argv[1:] if argv is None else argv)

    frontend_only = bool(args and args[0] == "--frontend")
    if frontend_only:
        args.pop(0)

    if len(args) > 1:
        _print_usage_error(len(args))
        return int(ExitCode.USAGE_ERROR)

    default = CliRequest()
    input_path = Path(args[0]) if args else default.input_path
    output_path = default.output_path

    try:
        if frontend_only:
            compile_file(input_path, output_path)
        else:
            compile_program(input_path, xml_path=output_path)
    except FrontendError as exc:
        print(exc.diagnostic.render(), file=sys.stderr)
        return int(exc.exit_code)
    except NameAnalysisError as exc:
        print(exc.render(), file=sys.stderr)
        return int(ExitCode.NAME_ERROR)
    except (TypeAnalysisError, NumericPolicyError) as exc:
        print(exc.render(), file=sys.stderr)
        return int(ExitCode.TYPE_ERROR)
    except FoundationError as exc:
        print(exc.render(), file=sys.stderr)
        return int(ExitCode.TREE_ERROR)
    except CodegenError as exc:
        print(exc.render(), file=sys.stderr)
        return int(ExitCode.GENERATION_ERROR)
    except Exception as exc:
        print(
            f"{input_path}: internal[INT-UNEXPECTED]: unexpected failure: {exc}",
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
        hint="usage: python -m spl_frontend [--frontend] [input.txt]",
    )
    print(diagnostic.render(), file=sys.stderr)
