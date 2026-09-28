"""Source file loading and validation for SPL."""

from dataclasses import dataclass
from pathlib import Path

from .diagnostics import Diagnostic, DiagnosticPhase, ExitCode, FrontendError


@dataclass(frozen=True, slots=True)
class SourceFile:
    """Immutable representation of a loaded source file."""

    path: Path
    text: str

    def __len__(self) -> int:
        return len(self.text)


def load_source(path: Path) -> SourceFile:
    """Load and validate an ASCII source file.

    Raises LexicalError if the file contains non-ASCII bytes.
    """
    raw_bytes = path.read_bytes()

    for offset, byte in enumerate(raw_bytes):
        if byte > 127:
            line, column = _compute_position(raw_bytes, offset)
            raise FrontendError(
                ExitCode.LEXICAL_ERROR,
                Diagnostic(
                    phase=DiagnosticPhase.LEXER,
                    code="LEX-NON-ASCII",
                    message=f"non-ASCII byte 0x{byte:02x} in source",
                    path=path,
                    line=line,
                    column=column,
                    hint="SPL source must contain only ASCII characters",
                ),
            )

    text = raw_bytes.decode("ascii")
    return SourceFile(path=path, text=text)


def _compute_position(data: bytes, offset: int) -> tuple[int, int]:
    """Compute one-based line and column for a byte offset."""
    line = 1
    column = 1
    i = 0
    while i < offset:
        if data[i] == 0x0D:  # CR
            if i + 1 < len(data) and data[i + 1] == 0x0A:
                i += 1  # Skip the LF in CRLF
            line += 1
            column = 1
        elif data[i] == 0x0A:  # LF
            line += 1
            column = 1
        else:
            column += 1
        i += 1
    return line, column
