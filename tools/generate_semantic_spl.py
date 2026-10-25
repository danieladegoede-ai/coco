"""Generate semantically valid SPL programs for backend testing.

Unlike generate_valid_spl.py which only produces syntactically valid programs,
this generator produces programs that:
1. Declare all variables before use
2. Only call functions that are direct children of the caller
3. Avoid mod+div and mod+decimal conflicts
4. Initialize variables before reading
5. Avoid recursive calls (direct or indirect)
6. Have known outputs computable by an independent oracle

Design:
- A local random.Random(seed) instance keeps generation reproducible
- Tracks declared variables and functions per scope
- Maintains numeric mode consistency (integer or float, not mixed)
- Generates programs that terminate and have predictable outputs
"""

from __future__ import annotations

import argparse
import random
import struct
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


DEFAULT_SEED = 0
DEFAULT_MAX_DEPTH = 4
DEFAULT_MAX_SIZE = 1024
DEFAULT_MAX_LOOPS = 8
DEFAULT_MAX_ITERATIONS = 5
DEFAULT_MAX_FUNCTION_DEPTH = 2
DEFAULT_MAX_STEPS = 10000


NumericMode = Literal["integer", "float"]


@dataclass
class Scope:
    """Track declared names and their properties in a scope."""
    variables: list[str] = field(default_factory=list)
    initialized: set[str] = field(default_factory=set)
    functions: dict[str, dict] = field(default_factory=dict)
    parent: Scope | None = None

    def all_variables(self) -> list[str]:
        """Get all accessible variables including from ancestors."""
        result = list(self.variables)
        if self.parent:
            result.extend(self.parent.all_variables())
        return result

    def all_initialized(self) -> set[str]:
        """Get all initialized variables including from ancestors."""
        result = set(self.initialized)
        if self.parent:
            result.update(self.parent.all_initialized())
        return result

    def get_initialized_vars(self) -> list[str]:
        """Get list of initialized variables accessible in this scope."""
        return [v for v in self.all_variables() if v in self.all_initialized()]


@dataclass(frozen=True, slots=True)
class SourceFacts:
    """Measurements of emitted source, including uncalled function bodies.

    Size counts lexer tokens (including the two mandatory colons). Expression
    depth counts nested arithmetic/comparison/logical operations and calls;
    literal/variable terms have depth zero. Function and control depths count
    nested declarations and branch/loop constructs respectively, starting at 0.
    """

    token_count: int
    expression_depth: int
    function_depth: int
    control_depth: int
    loop_count: int
    feature_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class GenerationFacts:
    source: SourceFacts
    # Actual iterations per source LOOP, in preorder; no generated loop is
    # inside a function or another loop, so these are also per-invocation counts.
    loop_iterations: tuple[int, ...]
    # Shared evaluator tick units: executed INSTRs plus loop tests.
    runtime_steps: int


def measure_semantic_source(source: str) -> SourceFacts:
    """Measure the actual parsed source; independent of construction counters."""
    from spl_frontend.lexer import tokenize
    from spl_frontend.parser import parse
    from spl_frontend.source import SourceFile
    from spl_frontend.tree import NodeKind, SyntaxTree

    path = Path("generated.spl")
    tree = SyntaxTree()
    parse(tokenize(SourceFile(path, source)), tree, path)
    assert tree.root is not None
    features: Counter[str] = Counter()
    tokens = expression_depth = function_depth = control_depth = 0
    stack = [(tree.root, 0, 0, 0)]
    while stack:
        node, expr, func, control = stack.pop()
        if node.kind is NodeKind.LEAF:
            tokens += 1
            continue
        children = [tree.get_node(cid) for cid in node.child_ids]
        first = children[0].contents if children else ""
        if node.contents == "CALL":
            expr += 1
            features["call"] += 1
        elif node.contents == "BOOL" or (node.contents == "TERM" and first in
                ("add", "sub", "mul", "neg", "mod", "div")):
            expr += 1
            features[first] += 1
        elif node.contents == "F_TYPE":
            func += 1
            features[first] += 1
        elif node.contents in ("BRANCH", "LOOP"):
            control += 1
            if node.contents == "BRANCH":
                features["if"] += 1
            else:
                cond = children[0] if first == "COND" else children[4]
                kind = tree.get_node(cond.child_ids[0]).contents
                features[("pre_" if first == "COND" else "post_") + kind] += 1
                features["loop"] += 1
        elif node.contents == "INSTR" and first in ("nop", "comment", "print"):
            features[first] += 1
        expression_depth = max(expression_depth, expr)
        function_depth = max(function_depth, func)
        control_depth = max(control_depth, control)
        stack.extend((child, expr, func, control) for child in reversed(children))
    return SourceFacts(tokens, expression_depth, function_depth, control_depth,
                       features["loop"], tuple(sorted(features.items())))


@dataclass(slots=True)
class SemanticGenerator:
    """Generate valid source within hard, independently measurable limits.

    max_size is a total lexer-token ceiling, not a feature budget. max_depth
    caps both expression depth and nested control constructs. max_loops caps
    the total source LOOP count, not just loop nesting. max_iterations caps
    each loop's actual iterations. max_steps caps the shared runtime tick
    count, including calls and loop tests. A valid program needs two tokens;
    smaller size requests fail explicitly. Other zero bounds are supported.

    Expected events/iteration/step counts come from the construction model,
    never the compiler backend or reference evaluator. Source facts are checked
    before any result is returned. Small budgets select smaller scenarios.
    """

    rng: random.Random
    max_depth: int
    max_size: int
    max_loops: int = DEFAULT_MAX_LOOPS
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    numeric_mode: NumericMode = "integer"
    max_function_depth: int = DEFAULT_MAX_FUNCTION_DEPTH
    max_steps: int = DEFAULT_MAX_STEPS
    facts: GenerationFacts | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.numeric_mode not in ("integer", "float"):
            raise ValueError("numeric_mode must be integer or float")
        for name in ("max_depth", "max_size", "max_loops", "max_iterations",
                     "max_function_depth", "max_steps"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.max_size < 2:
            raise ValueError("max_size must be at least 2 for the mandatory ': :' tokens")

    def _facts(self, source: str, iterations: tuple[int, ...], steps: int) -> GenerationFacts:
        return GenerationFacts(measure_semantic_source(source), iterations, steps)

    def _fits(self, facts: GenerationFacts) -> bool:
        source = facts.source
        return (source.token_count <= self.max_size
                and source.expression_depth <= self.max_depth
                and source.control_depth <= self.max_depth
                and source.function_depth <= self.max_function_depth
                and source.loop_count <= self.max_loops
                and len(facts.loop_iterations) == source.loop_count
                and all(0 <= n <= self.max_iterations for n in facts.loop_iterations)
                and facts.runtime_steps <= self.max_steps)

    def generate(self) -> tuple[str, list[str]]:
        self.facts = None
        source, expected, iterations, steps = self._coverage_candidate()
        facts = self._facts(source, iterations, steps)
        if not self._fits(facts):
            source, expected, iterations, steps = self._small_candidate()
            facts = self._facts(source, iterations, steps)
        if not self._fits(facts):
            raise AssertionError("generator emitted source outside its bounds")
        self.facts = facts
        return source, expected

    def _small_candidate(self) -> tuple[str, list[str], tuple[int, ...], int]:
        # Every candidate stands alone. Never truncate source or expected events.
        a, b = self.rng.randint(2, 9), self.rng.randint(2, 9)
        # .5 is grammar-valid (fractional trailing zero is forbidden) and
        # exactly representable in binary32, keeping this model independent.
        x, y = (a + 0.5, b + 0.5) if self.numeric_mode == "float" else (a, b)
        left, right = str(x), str(y)
        terms = [(left, x)]
        if self.max_depth >= 1:
            terms.append((f"add ( {left} {right} )", x + y))
        if self.max_depth >= 2:
            terms.append((f"sub ( mul ( {left} {right} ) neg ( {left} ) )", x * y + x))
        source, expected, steps = ": : ", [], 0
        for term, value in terms:
            candidate = f": : print ( {term} ) ; "
            if self._fits(self._facts(candidate, (), 1)):
                source, expected, steps = candidate, [format(value, ".6g")], 1
        iterations: tuple[int, ...] = ()
        if self.max_depth and self.max_iterations:
            limit = self.rng.randint(1, min(self.max_iterations, 4))
            for i, form in enumerate(self._loop_forms(limit)[:self.max_loops]):
                body = "print ( #c ) ; #c = add ( #c 1 ) ;"
                prefix = "#c " if not iterations else ""
                candidate = prefix + source + "#c = 0 ; " + form.replace("BODY", body) + " ; "
                counts = iterations + (limit,)
                # Initialization + LOOP instruction + tests + two body INSTRs.
                cost = 2 + 3 * limit + (1 if i < 2 else 0)
                if self._fits(self._facts(candidate, counts, steps + cost)):
                    source = candidate
                    expected += [str(n) for n in range(limit)]
                    iterations, steps = counts, steps + cost
        return source, expected, iterations, steps

    @staticmethod
    def _loop_forms(limit: int) -> list[str]:
        return [
            f"while lesser ( #c {limit} ) do {{ BODY }}",
            f"until eq ( #c {limit} ) do {{ BODY }}",
            f"do {{ BODY }} while lesser ( #c {limit} )",
            f"do {{ BODY }} until eq ( #c {limit} )",
        ]

    def _coverage_candidate(self) -> tuple[str, list[str], tuple[int, ...], int]:
        a, b = self.rng.randint(2, 9), self.rng.randint(2, 9)
        expected: list[str] = []
        def number(value: int | float) -> str:
            return format(value, ".6g")
        op = "mod" if self.numeric_mode == "integer" else "div"
        ratio = a % b if op == "mod" else struct.unpack("=f", struct.pack("=f", a / b))[0]
        arithmetic = f"sub ( mul ( {a} {b} ) neg ( {a} ) )"

        functions = (
            "num #touch ( ) { : : #x = add ( #x 1 ) ; return ( #x ) } "
            "num #pair ( #a #b ) { : : return ( sub ( #a #b ) ) } "
            "void #show ( #p ) { : : print ( #p ) ; return } "
            "num #outer ( #p ) { #q : "
            "num #child ( ) { : : #q = add ( #q 1 ) ; "
            "return ( add ( #p add ( #q #x ) ) ) } "
            ": #q = 2 ; return ( #child ( ) ) } "
        )
        algo = [
            f"#x = {a} ; #r = #pair ( #x #touch ( ) ) ; print ( #r ) ;",
            "#r = #outer ( 4 ) ; print ( #r ) ; #show ( #r ) ;",
            "#r = #outer ( 1 ) ; print ( #r ) ;",
            f"#r = {arithmetic} ; print ( #r ) ;",
            f"#r = {op} ( {a} {b} ) ; print ( #r ) ;",
            'comment "moddiv.!" ; nop ; print "done" ;',
            # Neither skipped touch may change x. Nested and/or/not cover both
            # direct destinations and nested Boolean control flow.
            'if and ( eq ( 0 1 ) eq ( #touch ( ) 0 ) ) then { print "bad" ; } else { print "and" ; } ;',
            'if or ( eq ( 1 1 ) eq ( #touch ( ) 0 ) ) then { print "or" ; } else { print "bad" ; } ;',
            'if not ( or ( lesser ( 3 2 ) larger ( 1 2 ) ) ) then { print "not" ; } else { print "bad" ; } ;',
            'print ( #x ) ;',
        ]
        expected.extend(["-1", str(a + 8), str(a + 8), str(a + 5),
                         str(a * b + a), number(ratio), "done", "and", "or", "not", str(a + 1)])
        iterations: list[int] = []
        steps = 28
        if self.max_loops and self.max_iterations:
            limit = self.rng.randint(1, min(self.max_iterations, 4))
            forms = self._loop_forms(limit)
            for i, form in enumerate(forms[:self.max_loops]):
                body = "print ( #c ) ; #c = add ( #c 1 ) ;"
                algo.append("#c = 0 ; " + form.replace("BODY", body) + " ;")
                expected.extend(str(i) for i in range(limit))
                iterations.append(limit)
                steps += 2 + 3 * limit + (1 if i < 2 else 0)
            # Pretests can skip completely; posttests must run at least once.
            boundaries = [
                ('while eq ( 0 1 ) do { print "bad" ; } ;', 0, 2),
                ('until eq ( 1 1 ) do { print "bad" ; } ;', 0, 2),
                ('do { print "once" ; } while eq ( 0 1 ) ;', 1, 3),
                ('do { print "once" ; } until eq ( 1 1 ) ;', 1, 3),
            ]
            for fragment, count, cost in boundaries[:max(0, self.max_loops - len(iterations))]:
                algo.append(fragment)
                iterations.append(count)
                steps += cost
                if count:
                    expected.append("once")
        return ("#x #r #c : " + functions + ": " + " ".join(algo) + " ",
                expected, tuple(iterations), steps)



def generate_semantic_program(
    seed: int = DEFAULT_SEED,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_size: int = DEFAULT_MAX_SIZE,
    numeric_mode: NumericMode = "integer",
    *,
    max_loops: int = DEFAULT_MAX_LOOPS,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    max_function_depth: int = DEFAULT_MAX_FUNCTION_DEPTH,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> tuple[str, list[str]]:
    """Generate a semantically valid SPL program.

    Returns (source_code, expected_outputs). See SemanticGenerator for hard
    limit units and its .facts snapshot; max_size below 2 is impossible.
    """
    gen = SemanticGenerator(
        rng=random.Random(seed),
        max_depth=max_depth,
        max_size=max_size,
        numeric_mode=numeric_mode,
        max_loops=max_loops,
        max_iterations=max_iterations,
        max_function_depth=max_function_depth,
        max_steps=max_steps,
    )
    return gen.generate()


def generate_coverage_program(seed: int = DEFAULT_SEED,
                              numeric_mode: NumericMode = "integer") -> tuple[str, list[str]]:
    """Guaranteed complete scenario with explicit adequate default limits.

    Eight loops cover four repeating forms and four zero/one-iteration
    boundaries. Depth 4, 1024 tokens, two function levels and 10000 runtime
    steps accommodate the complete scenario for every supported seed/mode.
    """
    return generate_semantic_program(seed, 4, 1024, numeric_mode,
                                     max_loops=8, max_iterations=5,
                                     max_function_depth=2, max_steps=10000)


def generate_anchored_programs() -> list[tuple[str, str, list[str]]]:
    """Generate fixed programs with known exact outputs for oracle testing.

    Returns list of (name, source, expected_outputs).
    """
    programs = []

    programs.append((
        "simple_print",
        ': : print "hello" ; ',
        ["hello"],
    ))

    programs.append((
        "arithmetic_add",
        '#x : : #x = add ( 5 3 ) ; print ( #x ) ; ',
        ["8"],
    ))

    programs.append((
        "arithmetic_mul_sub",
        '#x : : #x = sub ( mul ( 4 3 ) 2 ) ; print ( #x ) ; ',
        ["10"],
    ))

    programs.append((
        "mod_operation",
        '#x : : #x = mod ( 17 5 ) ; print ( #x ) ; ',
        ["2"],
    ))

    programs.append((
        "div_operation",
        '#x : : #x = div ( 5 2 ) ; print ( #x ) ; ',
        ["2.5"],
    ))

    programs.append((
        "nested_function",
        '#r : num #f ( #a ) { : : return ( add ( #a 1 ) ) } : #r = #f ( 5 ) ; print ( #r ) ; ',
        ["6"],
    ))

    programs.append((
        "if_branch_true",
        ': : if larger ( 5 3 ) then { print "yes" ; } else { print "no" ; } ; ',
        ["yes"],
    ))

    programs.append((
        "if_branch_false",
        ': : if lesser ( 5 3 ) then { print "yes" ; } else { print "no" ; } ; ',
        ["no"],
    ))

    programs.append((
        "while_loop",
        '#c : : #c = 0 ; while lesser ( #c 3 ) do { print "loop" ; #c = add ( #c 1 ) ; } ; ',
        ["loop", "loop", "loop"],
    ))

    programs.append((
        "void_function",
        ': void #greet ( ) { : : print "hi" ; return } : #greet ( ) ; ',
        ["hi"],
    ))

    return programs


def main(argv: list[str] | None = None) -> int:
    """Generate semantic SPL programs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed", type=int, nargs="?", default=DEFAULT_SEED)
    parser.add_argument("output", type=Path, nargs="?", default=Path("semantic_spl.txt"))
    parser.add_argument("--float", dest="float_mode", action="store_true")
    parser.add_argument("--anchors", type=Path, nargs="?", const=Path("."))
    parser.add_argument("--max-size", type=int, default=DEFAULT_MAX_SIZE)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--max-loops", type=int, default=DEFAULT_MAX_LOOPS)
    parser.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS)
    parser.add_argument("--max-function-depth", type=int, default=DEFAULT_MAX_FUNCTION_DEPTH)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    args = parser.parse_args(argv)
    if args.anchors is not None:
        args.anchors.mkdir(parents=True, exist_ok=True)
        for name, source, outputs in generate_anchored_programs():
            path = args.anchors / f"{name}.spl"
            path.write_text(source, encoding="ascii")
            print(f"wrote {path}")
        return 0
    seed, out = args.seed, args.output
    mode: NumericMode = "float" if args.float_mode else "integer"
    try:
        source, outputs = generate_semantic_program(
            seed=seed, numeric_mode=mode, max_size=args.max_size,
            max_depth=args.max_depth, max_loops=args.max_loops,
            max_iterations=args.max_iterations, max_function_depth=args.max_function_depth,
            max_steps=args.max_steps)
    except ValueError as exc:
        parser.error(str(exc))
    out.write_text(source, encoding="ascii")
    print(f"wrote {out} (seed={seed}, mode={mode})")
    print(f"expected outputs: {outputs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
