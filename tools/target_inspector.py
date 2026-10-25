"""Inspect the restricted generated C++ dialect, excluding comments/literals.

This is a structural acceptance check, not a replacement for compiling C++.
In particular, arbitrary external C++ identifiers remain the native compiler's
responsibility; SPL storage and control-flow identities are checked here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class CppToken:
    value: str
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class TargetIssue:
    code: str
    message: str
    line: int | None = None


_TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+(?:\.[0-9]*)?|::|&&|\|\||!=|==|<=|>=|[^\s]")
_STORAGE = re.compile(r"spl_(?:[vp][0-9]+|(?:tmp|exp|cap|ret)_[0-9]+)\Z")
_SPLICE = re.compile(r"\\\r?\n")
_DIRECTIVE = re.compile(r"#[ \t]*(?:include|pragma|define|undef|if|ifdef|ifndef|elif|else|endif|error|line)\b")
_RAW_STRING = re.compile(r'(?:u8|u|U|L)?R"([^ ()\\\t\r\n]{0,16})\(')
_QUOTED = re.compile(r'''(?:u8|u|U|L)?(["'])''')


def tokenize_cpp_executable(source: str) -> tuple[CppToken, ...]:
    """Tokenize executable text after C++ line splicing, retaining line numbers."""
    # C++ splices *before* recognizing comments. Retain an index map so a
    # continuation in a comment/string cannot create false executable tokens.
    chars: list[str] = []
    positions: list[tuple[int, int]] = []
    line = column = 1
    offset = 0
    while offset < len(source):
        splice = _SPLICE.match(source, offset) if source[offset] == "\\" else None
        if splice:
            offset += len(splice[0])
            line += 1
            column = 1
            continue
        char = source[offset]
        chars.append(char)
        positions.append((line, column))
        if char == "\n":
            line, column = line + 1, 1
        else:
            column += 1
        offset += 1
    text = "".join(chars)
    result: list[CppToken] = []
    offset = 0
    while offset < len(text):
        if text[offset].isspace():
            offset += 1
            continue
        if text.startswith("//", offset):
            end = text.find("\n", offset + 2)
            offset = len(text) if end < 0 else end
            continue
        if text.startswith("/*", offset):
            end = text.find("*/", offset + 2)
            offset = len(text) if end < 0 else end + 2
            continue
        if _DIRECTIVE.match(text, offset) and not text[text.rfind("\n", 0, offset) + 1:offset].strip():
            end = text.find("\n", offset + 1)
            offset = len(text) if end < 0 else end
            continue
        raw = _RAW_STRING.match(text, offset)
        if raw:
            end = text.find(")" + raw[1] + '"', offset + len(raw[0]))
            offset = len(text) if end < 0 else end + len(raw[1]) + 2
            continue
        quoted = _QUOTED.match(text, offset)
        if quoted:
            quote = quoted[1]
            offset += len(quoted[0])
            while offset < len(text):
                if text[offset] == "\\":
                    offset += 2
                elif text[offset] == quote:
                    offset += 1
                    break
                else:
                    offset += 1
            continue
        token = _TOKEN.match(text, offset)
        assert token is not None
        line, column = positions[offset]
        result.append(CppToken(token[0], line, column))
        offset = token.end()
    return tuple(result)


def inspect_target(source: str) -> tuple[TargetIssue, ...]:
    tokens = tokenize_cpp_executable(source)
    values = [token.value for token in tokens]
    issues: list[TargetIssue] = []

    def issue(code: str, message: str, index: int | None = None) -> None:
        issues.append(TargetIssue(code, message, tokens[index].line if index is not None else None))

    mains = [i for i, value in enumerate(values[:-1]) if value == "main" and values[i + 1] == "("]
    if len(mains) != 1:
        issue("TARGET-MAIN-COUNT", f"Expected one main, found {len(mains)}.")
    returns = [i for i, value in enumerate(values) if value == "return"]
    if len(returns) != 1:
        issue("TARGET-RETURN-COUNT", f"Expected one final return, found {len(returns)}.")
    elif values[returns[0]:] != ["return", "0", ";", "}"]:
        issue("TARGET-FINAL-RETURN", "Expected final return 0 at the end of main.", returns[0])

    definitions: Counter[str] = Counter()
    gotos: list[tuple[str, int]] = []
    declared: set[str] = set()
    for i, value in enumerate(values):
        following = values[i + 1] if i + 1 < len(values) else None
        if following == ":" and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value):
            definitions[value] += 1
        if value == "goto" and following is not None:
            gotos.append((following, i))
        if value in {"int", "double", "float"} and following and _STORAGE.fullmatch(following):
            if following in declared:
                issue("TARGET-DUPLICATE-STORAGE", f"Storage {following} is declared twice.", i)
            declared.add(following)
        if value == "else":
            issue("TARGET-PROHIBITED-ELSE", "Executable else is prohibited.", i)
        if value in {"&&", "||", "!", "and", "or", "not"}:
            issue("TARGET-PROHIBITED-BOOLEAN", f"Executable Boolean composition {value} is prohibited.", i)
        if value == "#":
            issue("TARGET-RAW-SPL-NAME", "Raw SPL name in executable code.", i)
        if re.fullmatch(r"spl_f[0-9]+", value) and following == "(":
            issue("TARGET-RUNTIME-SPL-CALL", f"Runtime SPL call {value} was not inlined.", i)
    for label, count in definitions.items():
        if count > 1:
            issue("TARGET-DUPLICATE-LABEL", f"Label {label} has {count} definitions.")
    for target, i in gotos:
        if target not in definitions:
            issue("TARGET-DANGLING-GOTO", f"Undefined goto target {target}.", i)
    for i, value in enumerate(values):
        if _STORAGE.fullmatch(value) and value not in declared:
            issue("TARGET-UNDECLARED-STORAGE", f"Undeclared storage {value}.", i)
    return tuple(issues)
