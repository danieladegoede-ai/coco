"""Approved command-line defaults shared with the driver and tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_INPUT_PATH = Path("SPL.txt")
DEFAULT_OUTPUT_PATH = Path("tree.xml")
EXECUTABLE_NAME = "splc"


@dataclass(frozen=True, slots=True)
class CliRequest:
    """Resolved paths for one front-end command invocation."""

    input_path: Path = DEFAULT_INPUT_PATH
    output_path: Path = DEFAULT_OUTPUT_PATH
