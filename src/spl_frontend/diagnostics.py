"""Structured diagnostics shared by all front-end modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from pathlib import Path


class DiagnosticPhase(str, Enum):
    DRIVER = "driver"
    LEXER = "lexer"
    SYNTAX = "syntax"
    TREE = "tree"
    INTERNAL = "internal"


class ExitCode(IntEnum):
    SUCCESS = 0
    USAGE_ERROR = 2
    INPUT_ERROR = 3
    LEXICAL_ERROR = 4
    SYNTAX_ERROR = 5
    TREE_ERROR = 6
    INTERNAL_ERROR = 70


@dataclass(frozen=True, slots=True)
class Diagnostic:
    phase: DiagnosticPhase
    code: str
    message: str
    path: Path
    line: int
    column: int
    hint: str | None = None

    def __post_init__(self) -> None:
        if self.line < 1 or self.column < 1:
            raise ValueError("Diagnostic line and column must be one or greater.")
        if not self.code:
            raise ValueError("Diagnostic code cannot be empty.")
        if not self.message:
            raise ValueError("Diagnostic message cannot be empty.")

    def render(self) -> str:
        result = (
            f"{self.path}:{self.line}:{self.column}: "
            f"{self.phase.value}[{self.code}]: {self.message}"
        )
        if self.hint:
            result += f"\nhint: {self.hint}"
        return result


class FrontendError(Exception):
    """Expected front-end failure carrying a diagnostic and process status."""

    def __init__(self, exit_code: ExitCode, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.exit_code = exit_code
        self.diagnostic = diagnostic
