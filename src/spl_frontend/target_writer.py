"""Deterministic writer for validated C++17 target programs.

The writer is intentionally a serializer, not a code generator: it only accepts
validated typed IR. All declarations are hoisted to the beginning of ``main``
so gotos never jump over a declaration with initialization. Labels always
include an empty statement, making terminal/adjacent labels legal C++.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile

from spl_frontend.codegen_ir import (
    Assign,
    BinaryAssign,
    CodegenError,
    Comment,
    ConditionalJump,
    Jump,
    Label,
    Nop,
    NumberLiteral,
    PrintNumber,
    PrintString,
    StorageRef,
    TargetProgram,
    TargetScalarType,
    UnaryAssign,
    FreshNameAllocator,
)
from spl_frontend.semantic_model import NumericMode, Symbol


_RAW_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _cpp_string_literal(value: str) -> str:
    """Return a valid C++ string literal without relying on shell escaping."""
    pieces = ['"']
    for char in value:
        codepoint = ord(char)
        if char == "\\":
            pieces.append("\\\\")
        elif char == '"':
            pieces.append('\\"')
        elif char == "\n":
            pieces.append("\\n")
        elif char == "\r":
            pieces.append("\\r")
        elif char == "\t":
            pieces.append("\\t")
        elif codepoint < 32 or codepoint == 127:
            pieces.append(f"\\{codepoint:03o}")
        else:
            pieces.append(char)
    pieces.append('"')
    return "".join(pieces)


def _target_type(value_type: TargetScalarType) -> str:
    if value_type is TargetScalarType.INTEGER:
        return "int"
    if value_type is TargetScalarType.FLOAT:
        return "float"
    raise CodegenError("WRITE-TYPE", f"Unsupported target scalar type {value_type!r}.")


def _comment_lines(text: str, *, prefix: str = "// ") -> list[str]:
    # splitlines avoids allowing arbitrary payload newlines to escape a comment.
    lines = text.splitlines()
    if not lines:
        return [prefix.rstrip()]
    # Translation phase 2 of C++ removes backslash-newline pairs before
    # recognizing comments. Do not let a payload swallow the next statement.
    return [prefix + line + (" ." if line.rstrip().endswith("\\") else "") for line in lines]


class TargetWriter:
    """Render one :class:`TargetProgram` as deterministic C++ source."""

    def render(self, program: TargetProgram) -> str:
        if not isinstance(program, TargetProgram):
            raise CodegenError("WRITE-PROGRAM", "TargetWriter requires a TargetProgram.")
        program.validate()
        lines = []
        for section in program.code_mine:
            lines.append("")
            lines.extend(_comment_lines(f"--- BEGIN CODE MINE: {section.name} ---"))
            # Never use an outer /* ... */ block: arbitrary templates may contain
            # comment terminators and must remain completely non-executable.
            lines.extend(_comment_lines(section.text))
            lines.extend(_comment_lines(f"--- END CODE MINE: {section.name} ---"))

        lines.extend(["#include <iostream>", "", "int main() {"])

        # No declaration is emitted among the jumps/labels. Empty initialization
        # provides deterministic values even where the source language permits an
        # undeclared initial value, and is legal with forward/backward gotos.
        for symbol_id in program.declared_symbol_ids:
            symbol = program.symbols[symbol_id]
            target_type = _target_type(TargetScalarType.from_mode(program.numeric_mode))
            lines.append(f"    {target_type} {self._symbol_name(symbol)}{{}};")
        for storage in program.fragment.declarations:
            name = FreshNameAllocator.storage_name(storage)
            self._require_identifier(name)
            target_type = _target_type(storage.value_type)
            lines.append(f"    {target_type} {name}{{}};")

        if program.declared_symbol_ids or program.fragment.declarations:
            lines.append("")
        for instruction in program.fragment.instructions:
            emitted = self._render_instruction(instruction, program)
            lines.extend(emitted)
        if program.fragment.instructions:
            lines.append("")
        lines.append("    return 0;")
        lines.append("}")


        return "\n".join(lines) + "\n"

    @staticmethod
    def _symbol_name(symbol: Symbol) -> str:
        name = symbol.internal_name
        TargetWriter._require_identifier(name)
        if name.startswith(("spl_tmp_", "spl_lbl_", "spl_exp_", "spl_cap_", "spl_ret_")):
            raise CodegenError("WRITE-NAMESPACE", f"Symbol name {name!r} collides with a generated namespace.")
        return name

    @staticmethod
    def _require_identifier(name: str) -> None:
        if not _RAW_IDENTIFIER.fullmatch(name):
            raise CodegenError("WRITE-IDENTIFIER", f"Unsafe target identifier {name!r}.")

    @staticmethod
    def _operand(value, program: TargetProgram) -> str:
        from spl_frontend.codegen_ir import StorageRef, SymbolRef

        if isinstance(value, StorageRef):
            return FreshNameAllocator.storage_name(value)
        if isinstance(value, SymbolRef):
            symbol = program.symbols.get(value.symbol_id)
            if symbol is None:
                raise CodegenError("WRITE-UNKNOWN-SYMBOL", f"Unknown symbol {value.symbol_id}.")
            return TargetWriter._symbol_name(symbol)
        if isinstance(value, NumberLiteral):
            lexeme = value.lexeme
            if program.numeric_mode is NumericMode.FLOAT:
                return (lexeme if "." in lexeme else lexeme + ".0") + "f"
            return lexeme
        raise CodegenError("WRITE-OPERAND", f"Cannot render operand {value!r}.")

    def _render_instruction(self, instruction, program: TargetProgram) -> list[str]:
        indent = "    "
        if isinstance(instruction, Assign):
            return [f"{indent}{self._operand(instruction.target, program)} = {self._operand(instruction.value, program)};"]
        if isinstance(instruction, BinaryAssign):
            left = self._operand(instruction.left, program)
            right = self._operand(instruction.right, program)
            target = self._operand(instruction.target, program)
            return [f"{indent}{target} = ({left} {instruction.operator.value} {right});"]
        if isinstance(instruction, UnaryAssign):
            target = self._operand(instruction.target, program)
            value = self._operand(instruction.value, program)
            return [f"{indent}{target} = (-({value}));"]
        if isinstance(instruction, PrintNumber):
            return [f"{indent}std::cout << {self._operand(instruction.value, program)};"]
        if isinstance(instruction, PrintString):
            return [f"{indent}std::cout << {_cpp_string_literal(instruction.value.value)};"]
        if isinstance(instruction, Nop):
            return [f"{indent}// nop"]
        if isinstance(instruction, Comment):
            return _comment_lines(instruction.text, prefix=indent + "// ")
        if isinstance(instruction, Label):
            label_name = FreshNameAllocator.label_name(instruction.label)
            self._require_identifier(label_name)
            # A label must precede a statement in C++. A null statement also
            # makes an otherwise empty block and a terminal label legal.
            return [f"{label_name}: ;"]
        if isinstance(instruction, Jump):
            label_name = FreshNameAllocator.label_name(instruction.target)
            self._require_identifier(label_name)
            return [f"{indent}goto {label_name};"]
        if isinstance(instruction, ConditionalJump):
            left = self._operand(instruction.left, program)
            right = self._operand(instruction.right, program)
            true_name = FreshNameAllocator.label_name(instruction.true_target)
            false_name = FreshNameAllocator.label_name(instruction.false_target)
            self._require_identifier(true_name)
            self._require_identifier(false_name)
            return [
                f"{indent}if ({left} {instruction.operator.value} {right}) goto {true_name};",
                f"{indent}goto {false_name};",
            ]
        raise CodegenError("WRITE-INSTRUCTION", f"Unsupported target instruction {instruction!r}.")


def render_target(program: TargetProgram) -> str:
    """Convenience API for deterministic serialization of a validated program."""
    return TargetWriter().render(program)


def write_target(program: TargetProgram, output_path: Path) -> None:
    """Atomically publish validated target source to an existing directory."""
    if not isinstance(output_path, Path):
        raise CodegenError("WRITE-PATH", "Target output path must be a pathlib.Path.")
    rendered = render_target(program)  # Validate before touching an existing file.
    parent = output_path.parent
    if not parent.is_dir():
        raise CodegenError("WRITE-DIRECTORY", f"Output directory does not exist: {parent}")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=parent,
            prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, output_path)
        temporary_name = None
    except OSError as exc:
        raise CodegenError("WRITE-OUTPUT", f"Cannot write target output {output_path}: {exc}") from exc
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
