"""Generate one-fault mutations of valid SPL programs for negative testing.

Design:
- A mutation takes a valid SPL program string and changes exactly one thing.
- The mutation is chosen by a seeded random.Random instance, making it
  reproducible across runs.
- Each mutation returns a Mutation record containing the mutated program,
  a human-readable description, and the approximate location of the fault.

This module never imports the parser or lexer. It only manipulates text and
is intended to feed the CLI's negative test suite.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MutationKind(str, Enum):
    REMOVE_SEPARATOR = "remove-separator"
    REMOVE_SEMICOLON = "remove-semicolon"
    REMOVE_COLON = "remove-colon"
    REMOVE_BRACE = "remove-brace"
    REMOVE_PAREN = "remove-paren"
    REMOVE_KEYWORD = "remove-keyword"
    INSERT_UNEXPECTED = "insert-unexpected"
    CORRUPT_NAME = "corrupt-name"
    CORRUPT_NUMBER = "corrupt-number"
    TRUNCATE = "truncate"
    APPEND_TRAILING = "append-trailing"


KEYWORDS = (
    "void", "num", "return", "print", "nop", "comment",
    "if", "then", "else", "while", "until", "do",
    "not", "and", "or", "eq", "larger", "lesser",
    "mod", "add", "sub", "mul", "div", "neg",
)


@dataclass(frozen=True, slots=True)
class Mutation:
    """One single-fault mutation of an SPL program."""

    program: str
    kind: MutationKind
    description: str
    original_snippet: str


def _split_tokens(text: str) -> list[str]:
    """Split the program into whitespace-delimited tokens (approximate)."""
    return text.split()


def _positions_of(text: str, char: str) -> list[int]:
    return [i for i, c in enumerate(text) if c == char]


# ----------------------------------------------------------------------
# Individual mutations
# ----------------------------------------------------------------------


def _remove_separator(text: str, rng: random.Random) -> Mutation | None:
    """Delete a space between two tokens, joining them."""
    tokens = _split_tokens(text)
    if len(tokens) < 2:
        return None
    idx = rng.randrange(len(tokens) - 1)
    joined = tokens[idx] + tokens[idx + 1]
    new_tokens = tokens[:idx] + [joined] + tokens[idx + 2:]
    new_text = " ".join(new_tokens)
    if new_text == text:
        return None
    return Mutation(
        program=new_text,
        kind=MutationKind.REMOVE_SEPARATOR,
        description=f"joined tokens '{tokens[idx]}' and '{tokens[idx + 1]}'",
        original_snippet=f"{tokens[idx]} {tokens[idx + 1]}",
    )


def _remove_char(text: str, char: str, kind: MutationKind) -> Mutation | None:
    positions = _positions_of(text, char)
    if not positions:
        return None
    pos = positions[0]
    new_text = text[:pos] + text[pos + 1:]
    return Mutation(
        program=new_text,
        kind=kind,
        description=f"removed '{char}' at offset {pos}",
        original_snippet=text[max(0, pos - 10):pos + 11],
    )


def _remove_keyword(text: str, rng: random.Random) -> Mutation | None:
    tokens = _split_tokens(text)
    candidates = [i for i, t in enumerate(tokens) if t in KEYWORDS]
    if not candidates:
        return None
    idx = rng.choice(candidates)
    removed = tokens[idx]
    new_tokens = tokens[:idx] + tokens[idx + 1:]
    new_text = " ".join(new_tokens)
    return Mutation(
        program=new_text,
        kind=MutationKind.REMOVE_KEYWORD,
        description=f"removed keyword '{removed}'",
        original_snippet=removed,
    )


def _insert_unexpected(text: str, rng: random.Random) -> Mutation | None:
    tokens = _split_tokens(text)
    if not tokens:
        return None
    idx = rng.randrange(len(tokens) + 1)
    junk = rng.choice(["@", "$", "?", "&", "!"])
    new_tokens = tokens[:idx] + [junk] + tokens[idx:]
    new_text = " ".join(new_tokens)
    return Mutation(
        program=new_text,
        kind=MutationKind.INSERT_UNEXPECTED,
        description=f"inserted unexpected token '{junk}' at position {idx}",
        original_snippet=junk,
    )


def _corrupt_name(text: str, rng: random.Random) -> Mutation | None:
    tokens = _split_tokens(text)
    candidates = [i for i, t in enumerate(tokens) if t.startswith("#")]
    if not candidates:
        return None
    idx = rng.choice(candidates)
    original = tokens[idx]
    corrupted = "#" + original[1:].upper()
    new_tokens = list(tokens)
    new_tokens[idx] = corrupted
    new_text = " ".join(new_tokens)
    return Mutation(
        program=new_text,
        kind=MutationKind.CORRUPT_NAME,
        description=f"uppercased name '{original}' to '{corrupted}'",
        original_snippet=original,
    )


def _corrupt_number(text: str, rng: random.Random) -> Mutation | None:
    tokens = _split_tokens(text)
    candidates = [i for i, t in enumerate(tokens) if t.isdigit() and t != "0"]
    if not candidates:
        return None
    idx = rng.choice(candidates)
    original = tokens[idx]
    corrupted = "0" + original  # leading zero
    new_tokens = list(tokens)
    new_tokens[idx] = corrupted
    new_text = " ".join(new_tokens)
    return Mutation(
        program=new_text,
        kind=MutationKind.CORRUPT_NUMBER,
        description=f"prepended zero to number '{original}'",
        original_snippet=original,
    )


def _truncate(text: str, rng: random.Random) -> Mutation | None:
    tokens = _split_tokens(text)
    if ":" not in tokens:
        return None
    # A prefix ending before the first section separator cannot form P.
    # Arbitrary later cuts may end after a complete instruction because ALGO
    # is nullable, silently turning a negative test into a valid program.
    first_colon = tokens.index(":")
    prefix_length = rng.randint(1, first_colon + 1)
    new_text = " ".join(tokens[:prefix_length]) + " "
    return Mutation(
        program=new_text,
        kind=MutationKind.TRUNCATE,
        description=f"truncated before the first complete P at token {prefix_length}",
        original_snippet=" ".join(tokens[max(0, prefix_length - 2):prefix_length + 2]),
    )


def _append_trailing(text: str, rng: random.Random) -> Mutation | None:
    junk = rng.choice(["garbage ", "@ ", "? ", "unexpected "])
    new_text = text + junk
    return Mutation(
        program=new_text,
        kind=MutationKind.APPEND_TRAILING,
        description=f"appended trailing junk '{junk.strip()}'",
        original_snippet=junk.strip(),
    )


# ----------------------------------------------------------------------
# Dispatcher
# ----------------------------------------------------------------------


MUTATIONS = (
    _remove_separator,
    lambda t, r: _remove_char(t, ";", MutationKind.REMOVE_SEMICOLON),
    lambda t, r: _remove_char(t, ":", MutationKind.REMOVE_COLON),
    lambda t, r: _remove_char(t, "{", MutationKind.REMOVE_BRACE),
    lambda t, r: _remove_char(t, "}", MutationKind.REMOVE_BRACE),
    lambda t, r: _remove_char(t, "(", MutationKind.REMOVE_PAREN),
    lambda t, r: _remove_char(t, ")", MutationKind.REMOVE_PAREN),
    _remove_keyword,
    _insert_unexpected,
    _corrupt_name,
    _corrupt_number,
    _truncate,
    _append_trailing,
)


def mutate_program(text: str, seed: int = 0) -> Mutation:
    """Return a single-fault mutation of a valid SPL program.

    Tries mutations in a random order until one succeeds. Raises
    ValueError if no mutation applies to the given text.
    """
    rng = random.Random(seed)
    order = list(range(len(MUTATIONS)))
    rng.shuffle(order)

    for i in order:
        mutation = MUTATIONS[i](text, rng)
        if mutation is not None:
            return mutation

    raise ValueError("no applicable mutation for this input")


def mutate_file(
    input_path: Path,
    output_path: Path,
    seed: int = 0,
) -> Mutation:
    """Read a valid program, mutate it, write the result to output_path."""
    text = input_path.read_text(encoding="ascii")
    mutation = mutate_program(text, seed=seed)
    output_path.write_text(mutation.program, encoding="ascii")
    return mutation


def main(argv: list[str] | None = None) -> int:
    """CLI entry: python tools/mutate_spl.py <input> <output> [seed]."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        print("usage: python tools/mutate_spl.py <input> <output> [seed]",
              file=sys.stderr)
        return 2
    input_path = Path(args[0])
    output_path = Path(args[1])
    seed = int(args[2]) if len(args) >= 3 else 0

    try:
        mutation = mutate_file(input_path, output_path, seed=seed)
    except ValueError as exc:
        print(f"mutation failed: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {output_path} (seed={seed})")
    print(f"kind: {mutation.kind.value}")
    print(f"description: {mutation.description}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
