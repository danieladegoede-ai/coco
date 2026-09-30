"""Generate syntactically valid SPL programs for front-end testing.

Design:
- A local random.Random(seed) instance keeps generation reproducible and
  independent of the global random state.
- Every recursive production takes a depth budget. When the budget is
  exhausted, only non-recursive alternatives are chosen.
- An expansion budget bounds instructions and declarations; an independent
  concrete-tree node cap checks the complete generated result.
- A fixed coverage program exercises every grammar alternative when a
  deterministic all-productions case is needed.
- Every token is followed by a single space, as the SPL specification
  requires a blank_space after every token.
- The end-of-file meta-symbol $ is never emitted.


"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_SEED = 0
DEFAULT_MAX_DEPTH = 6
DEFAULT_MAX_SIZE = 40
DEFAULT_MAX_NODES = 1000


@dataclass(slots=True)
class Generator:
    """Depth- and size-limited forward generator for the SPL grammar."""

    rng: random.Random
    max_depth: int
    max_size: int
    names: list[str] = field(default_factory=list)
    _name_counter: int = 0
    _size_remaining: int = 0
    _nonterminal_count: int = 0

    def __post_init__(self) -> None:
        self._size_remaining = self.max_size

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tick(self) -> bool:
        """Consume one unit of size budget; False if exhausted."""
        if self._size_remaining <= 0:
            return False
        self._size_remaining -= 1
        return True

    def _node(self) -> None:
        """Count one original-grammar non-terminal expansion."""
        self._nonterminal_count += 1

    def node_count(self, program: str) -> int:
        """Count generated grammar nodes and terminal lexemes independently."""
        return self._nonterminal_count + len(program.split())

    def _new_name(self) -> str:
        self._name_counter += 1
        name = f"#x{self._name_counter} "
        self.names.append(name.strip())
        return name

    def _choose(self, *options: str) -> str:
        return self.rng.choice(options)

    # ------------------------------------------------------------------
    # Grammar rules
    # ------------------------------------------------------------------

    def spl_prog(self) -> str:
        self._node()
        return self.p(self.max_depth)

    def p(self, depth: int) -> str:
        self._node()
        return (
            self.v_decl(depth)
            + ": "
            + self.f_decl(depth)
            + ": "
            + self.algo(depth)
        )

    def v_decl(self, depth: int) -> str:
        self._node()
        # V_DECL is nullable. Deeper nesting prefers the empty case.
        if depth <= 0 or self.rng.random() < 0.4:
            return ""
        if not self._tick():
            return ""
        return self._new_name() + self.v_decl(depth - 1)

    def f_decl(self, depth: int) -> str:
        self._node()
        if depth <= 0 or self.rng.random() < 0.5:
            return ""
        if not self._tick():
            return ""
        return self.f_type(depth) + self.f_decl(depth - 1)

    def f_type(self, depth: int) -> str:
        self._node()
        kind = self._choose("void", "num")
        name = self._new_name()
        params = self.v_decl(depth - 1)
        body = self.p(depth - 1)
        if kind == "void":
            return f"{kind} {name}( {params}) {{ {body}return }} "
        term = self.term(depth - 1)
        return f"{kind} {name}( {params}) {{ {body}return ( {term}) }} "

    def algo(self, depth: int) -> str:
        self._node()
        # ALGO is nullable; deeper nesting prefers the empty case.
        if depth <= 0 or self.rng.random() < 0.35:
            return ""
        if not self._tick():
            return ""
        return self.instr(depth) + "; " + self.algo(depth - 1)

    def instr(self, depth: int) -> str:
        self._node()
        # Choose from every INSTR alternative.
        choice = self._choose(
            "print",
            "nop",
            "comment",
            "assign",
            "branch",
            "loop",
            "call",
        )
        if choice == "print":
            return "print " + self.outp(depth)
        if choice == "nop":
            return "nop "
        if choice == "comment":
            return "comment " + self.string()
        if choice == "assign":
            return self.assign(depth)
        if choice == "branch":
            return self.branch(depth)
        if choice == "loop":
            return self.loop(depth)
        return self.call(depth)

    def outp(self, depth: int) -> str:
        self._node()
        if self.rng.random() < 0.5:
            return "( " + self.term(depth) + ") "
        return self.string()

    def assign(self, depth: int) -> str:
        self._node()
        return self._new_name() + "= " + self.term(depth - 1)

    def call(self, depth: int) -> str:
        self._node()
        return self._new_name() + "( " + self.inputs(depth) + ") "

    def inputs(self, depth: int) -> str:
        self._node()
        if depth <= 0 or self.rng.random() < 0.5:
            return ""
        return self.term(depth - 1) + " " + self.inputs(depth - 1)

    def term(self, depth: int) -> str:
        self._node()
        if depth <= 0:
            return self._choose(self._new_name(), self.number())
        choice = self._choose(
            "name", "num", "call",
            "mod", "add", "sub", "mul", "div", "neg",
        )
        if choice == "name":
            return self._new_name()
        if choice == "num":
            return self.number()
        if choice == "call":
            return self.call(depth)
        if choice == "neg":
            return "neg ( " + self.term(depth - 1) + ") "
        # binary operators
        return (
            f"{choice} ( "
            + self.term(depth - 1)
            + self.term(depth - 1)
            + ") "
        )

    def branch(self, depth: int) -> str:
        self._node()
        cond = self.bool(depth - 1)
        then = self.algo(depth - 1)
        els = self.algo(depth - 1)
        return f"if {cond}then {{ {then}}} else {{ {els}}} "

    def loop(self, depth: int) -> str:
        self._node()  # LOOP
        self._node()  # COND, whose only child is while or until.
        cond = self._choose("while", "until")
        b = self.bool(depth - 1)
        body = self.algo(depth - 1)
        if self.rng.random() < 0.5:
            return f"{cond} {b}do {{ {body}}} "
        return f"do {{ {body}}} {cond} {b}"

    def bool(self, depth: int) -> str:
        self._node()
        if depth <= 0:
            return "eq ( " + self.term(0) + self.term(0) + ") "
        choice = self._choose("not", "and", "or", "eq", "larger", "lesser")
        if choice == "not":
            return "not ( " + self.bool(depth - 1) + ") "
        if choice in ("and", "or"):
            return (
                f"{choice} ( "
                + self.bool(depth - 1)
                + self.bool(depth - 1)
                + ") "
            )
        # binary relational operators over terms
        return (
            f"{choice} ( "
            + self.term(depth - 1)
            + self.term(depth - 1)
            + ") "
        )

    def string(self) -> str:
        # Simple, valid STRING: a quoted lowercase word.
        word = self.rng.choice(["ok", "hello", "note", "x", "value"])
        return f'"{word}" '

    def number(self) -> str:
        # Valid NUM: no leading zeros, no -0.
        if self.rng.random() < 0.5:
            return "0 "
        return str(self.rng.randint(1, 999)) + " "


# ----------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------


def generate_program(
    seed: int = DEFAULT_SEED,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_size: int = DEFAULT_MAX_SIZE,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> str:
    """Return valid SPL under independent expansion and tree-node bounds.

    ``max_size`` limits declaration/function/instruction expansions. The
    generated concrete tree must also fit ``max_nodes``. If an initial seeded
    choice exceeds that cap, generation retries with a smaller expansion
    budget; it never consults the lexer or parser it is intended to test.
    """
    if type(max_depth) is not int or max_depth < 0:
        raise ValueError("max_depth must be a non-negative integer")
    if type(max_size) is not int or max_size < 0:
        raise ValueError("max_size must be a non-negative integer")
    if type(max_nodes) is not int or max_nodes < 7:
        raise ValueError("max_nodes must be an integer of at least 7")

    budget = max_size
    while True:
        gen = Generator(random.Random(seed), max_depth, budget)
        program = gen.spl_prog()
        if gen.node_count(program) <= max_nodes:
            return program
        if budget == 0:
            raise AssertionError("minimal SPL_PROG exceeds the node cap")
        budget //= 2


def generate_to_file(
    path: Path,
    seed: int = DEFAULT_SEED,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_size: int = DEFAULT_MAX_SIZE,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> None:
    """Write one generated program to path."""
    text = generate_program(
        seed=seed, max_depth=max_depth, max_size=max_size, max_nodes=max_nodes
    )
    path.write_text(text, encoding="ascii")


def generate_coverage_program() -> str:
    """Return one deterministic valid program covering every production.

    This is deliberately independent of the lexer and parser. The generated
    test suite checks both its validity and its original-grammar derivations.
    """
    instructions = (
        'print "a"', "print ( 1 )", "nop", 'comment "b"',
        "#x = #y", "#x = 0", "#x = #f ( )",
        "#x = mod ( 1 2 )", "#x = add ( 1 2 )",
        "#x = sub ( 1 2 )", "#x = mul ( 1 2 )",
        "#x = div ( 1 2 )", "#x = neg ( 1 )",
        "#f ( )", "#f ( 1 #x )",
        "if not ( eq ( 1 2 ) ) then { } else { }",
        "if and ( eq ( 1 2 ) larger ( 2 1 ) ) then { } else { }",
        "if or ( lesser ( 1 2 ) eq ( 1 1 ) ) then { } else { }",
        "while eq ( 1 2 ) do { }",
        "until larger ( 2 1 ) do { }",
        "do { } while lesser ( 1 2 )",
        "do { } until eq ( 1 2 )",
    )
    return (
        "#x #y : void #v ( #p ) { : : return } "
        "num #n ( ) { : : return ( 1 ) } : "
        + " ; ".join(instructions) + " ; "
    )


def main(argv: list[str] | None = None) -> int:
    """Write a seeded program or the deterministic coverage program."""
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--coverage":
        if len(args) > 2:
            print("usage: generate_valid_spl.py --coverage [out_path]", file=sys.stderr)
            return 2
        out = Path(args[1]) if len(args) == 2 else Path("SPL.txt")
        out.write_text(generate_coverage_program(), encoding="ascii")
        print(f"wrote {out} (all grammar productions)")
        return 0
    seed = int(args[0]) if len(args) >= 1 else DEFAULT_SEED
    out = Path(args[1]) if len(args) >= 2 else Path("SPL.txt")
    generate_to_file(out, seed=seed)
    print(f"wrote {out} (seed={seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
