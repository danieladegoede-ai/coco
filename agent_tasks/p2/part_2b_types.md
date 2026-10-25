# Part 2b type and numeric analysis

Implementation: `numeric_policy.py`, `type_analysis.py`. Original owner: Kuda21
(u20620111), issues #24/#25; audit and integration work authorized by Rudolph
on 24 October 2026. This document describes implementation and local evidence;
team approvals, tutor answers and hosted checks are separate review gates.

## Public boundary

`check_types(resolved: ResolvedProgram) -> CheckedProgram` first applies the
whole-tree numeric scan, then seeds **all** signatures and visits the complete
tree bottom-up. A returned snapshot has known types for every nonterminal,
every bound name and every NUM. Its root is `OK`. Punctuation, operator keywords
and STRING leaves do not require separate numeric/Boolean attributes; absence
from `type_by_node` means no semantic attribute is assigned to that leaf.

The original tree, node IDs, binding map and symbols are preserved. Typed symbols
are copies in a new `ResolvedProgram`; the source locations remain available.
Repeated checking of one snapshot gives identical results and no cross-program
state leaks. `TypeAnalysisError` exposes code, message, node_id, expected/actual,
path/span and `render()`. Original source inputs report their actual SPL span;
XML-only inputs use node IDs without fabricated source positions. The integrating driver must supply an XML input path when rendering its
diagnostics; PR41 contains only the semantic APIs and the existing P1 CLI.

`scan_numeric_policy(tree) -> NumericScanResult` is an immutable result with
has_mod, has_div, has_decimal, mode, and the first relevant leaf node IDs.
Operators are recognized in TERM productions and NUMs at the leaf level;
quoted strings and comments are never searched for substrings. The scan is
linear in tree size, including every uncalled/nested body and return term.
`NumericPolicyError` exposes code/message/node_id/related_node_id/render.

## Full source-rule audit

All four complete pages of the official 2026 Part 2b sheet were reviewed,
including the final requirement that compliant programs receive no invented
type errors.

| Sheet | Production family | Implemented attribute/result |
|---|---|---|
| p1 | SPL_PROG, P | OK only when the required child productions are OK |
| p1 | V_DECL, nullable V_DECL | names numeric; declaration list OK |
| p1 | F_DECL, nullable F_DECL | all F_TYPE and tail OK |
| p1-p2 | void/num F_TYPE | signature procedure/numeric; parameters/body OK; num return numeric |
| p2 | ALGO, nullable ALGO | instruction and tail OK |
| p2 | OUTP, INSTR print/nop/comment | numeric term or STRING output; non-value instruction OK |
| p2 | INSTR ASSIGN/BRANCH/LOOP | propagate OK |
| p2 | INSTR CALL | procedure only; discarded numeric result rejected |
| p2 | CALL, INPUT, nullable INPUT | known bound function type; all actual terms numeric |
| p2 | ASSIGN; TERM NAME/NUM/CALL | numeric target/value; numeric call result required |
| p3 | mod/div global restrictions | exact required conflict; decimal NUM with any mod rejected |
| p3 | add/sub/mul/mod/div/neg | numeric operands, numeric result |
| p3 | comparisons, not/and/or | numeric comparisons produce Boolean; logical inputs Boolean |
| p3 | BRANCH; COND | Boolean condition, OK arms; while/until OK |
| p4 | both LOOP productions | Boolean condition, OK COND/body |

Semantic checking includes uncalled functions and validates all signatures
before processing calls. Source-language negative cases pass the actual lexer
and parser first; grammar-impossible forms are not advertised as source cases.

The priority of the two whole-tree conflicts is deterministic: mod+div first,
with exact message `A float-integer-conflict might perhaps be possible`, then
mod+decimal (`DECIMAL-WITH-MOD`). The type wrapper preserves this exact message
and the real source location. The scan does not require a decimal point on
integer-looking literals under div.

## Final release choices

The Speaker finalized these implementation choices without further consultation.
D01-D08 are recorded in the final release contract linked by `00_p2_decisions.md`.

- D05: integer with mod; float with div or any decimal literal; otherwise integer.
  The first two whole-tree restrictions are explicit sheet rules. Selecting a
  default mode and output representation for the remaining cases is a backend
  policy; the selected mode is passed once in `CheckedProgram`.
- D04: the supplied Part 2b CALL/INPUT rules contain no parameter-count check.
  Type analysis therefore accepts a type-correct mismatched count. Executable
  argument binding uses the backend's documented matching-count policy; that
  extra rule must not be described as an official Part 2b type error.
- D04: generated behavioral cases and oracle use left-to-right operand/actual
  evaluation and short-circuit and/or, matching the selected target lowering.
  The fixed tests expose side effects so an inconsistent stage cannot hide.
- Exact numeric equality and C++ truncation-toward-zero remainder are used by
  the oracle, matching the target operators. Numeric values use IEEE binary32 (`float`), rounded independently by the
  oracle at each literal/storage/arithmetic result with stdlib `struct`.
  Numeric print events use defaultfloat six significant digits; ordinary generated values stay small and
  finite. This does not impose a new source-language numeric magnitude rule.
- Separate variable/function namespaces and return-body name visibility are
  consumed from the existing Part 2a result, without claiming D06 is resolved.

## Semantic generator, independent oracle and mutation corpus

`tools/generate_semantic_spl.py` preserves the P1 syntax generator. Its public
`generate_semantic_program(seed, max_depth, max_size, numeric_mode)` returns
`(source, expected_output_events)`. The expected events are calculated directly
from the construction model, without importing compiler IR, target output or
the reference interpreter. All anchored examples now also contain complete
hand-computed expected events, including numeric outputs.

Default bounded scenarios guarantee arithmetic, all Boolean operators, true and
false paths, all four loops, skipped pretests and one-pass posttests, procedure
and numeric calls, repeated expansion, nested direct-child calls, parameter,
local and ancestor captures, and actual evaluation with visible side effects.
Integer and float suites use mutually exclusive mod/div. Every read is explicitly
initialized, divisors nonzero, counters cannot be overwritten by random code,
and iterations remain bounded.

The default budgets are explicit and adequate: 1024 total lexer tokens, expression
and control nesting depth 4, two function declaration levels, eight source LOOPs,
at most five iterations per loop, and 10000 runtime steps. These replace the
previous misleading feature budgets. `generate_coverage_program(seed, mode)`
requests those complete-coverage budgets explicitly; ordinary generation with
tighter limits selects a smaller complete scenario, retaining all its expected
events.

`max_size` is a hard ceiling on actual lexer tokens, including the two mandatory
colons. Values 0 and 1 raise ValueError because no valid SPL program fits; 2
returns `: : ` with no events. `max_depth=0` permits literal/variable terms but
no operations, calls, branches or loops. Depth counts nested arithmetic,
comparison, Boolean operations and calls; control depth separately counts
nested branch/loop constructs and is also capped by max_depth. Additional
keyword limits are `max_loops` (total source LOOP count), `max_iterations`
(actual iterations per loop), `max_function_depth`, and `max_steps` (executed
INSTRs plus loop tests, shared across calls). All other zero limits are supported.
These are generator constraints, not new language rejection rules.

`SemanticGenerator.facts` is an immutable `GenerationFacts` snapshot after
`generate()`: parsed `SourceFacts`, per-loop iteration counts in source preorder,
and the model's exact runtime step count. SourceFacts exposes token count,
expression/function/control depth, LOOP count and feature counters.
`measure_semantic_source(source)` independently measures the parsed source.
The generator checks every result against every requested bound. Tests also
observe actual interpreter body invocations and shared ticks to cross-check the
model's iteration/step counts, rather than trusting its counters alone. Seed 42
has a fully handwritten expected-event anchor (including capture effects and
all eight loops), independent of either runtime implementation.

The CLI accepts `--float` independently of positional seed/output, and exposes
all hard limits as `--max-size`, `--max-depth`, `--max-loops`, `--max-iterations`,
`--max-function-depth` and `--max-steps`.

`tools/reference_spl_evaluator.py` independently interprets the syntax tree.
Static acceptance uses the real frontend, but runtime values, control flow and
outputs never use backend IR/code generation. Hand-computed regression anchors
cover negative remainder signs, exact floating equality, float literal mode,
left-to-right capture, skipped side effects and a shared execution-step budget.
List traversal is iterative so long instruction/declaration/argument sequences
do not consume Python recursion. Uninitialized variables use a test-only zero
convention; generator cases never depend on that convention.

`tools/mutate_semantic_spl.py` requires a semantically valid baseline and inserts
one deliberate rule violation using parser leaf boundaries. It never mutates
text inside STRINGs. It supports undeclared/duplicate variables, void-in-term,
num-as-instruction, mod+div and decimal+mod, with deterministic expected phase,
code and seed. Inapplicable isolated mutations return None rather than silently
adding an independent second error.

`tests/fixtures/semantics/cases.json` references 40 curated inputs included in this change.
They include real positive/negative pairs for call typing in arithmetic,
negation, comparison, actuals, loop conditions and an uncalled nested return;
uncalled/deep numeric conflicts; and the Part 2a source-negative corpus.
`tests/generated/test_semantic_mutations.py` verifies parser success and exact
semantic failure for each mutation; the manifest acceptance test verifies all
40 files exist, parse, then reach their expected phase/code.

## Reproducible verification

Run from repository root with Python >=3.11 and `PYTHONPATH=src`:

```sh
python -m unittest tests.unit.test_numeric_policy tests.unit.test_type_analysis tests.unit.test_reference_spl_evaluator tests.generated.test_semantic_generator tests.generated.test_semantic_mutations tests.integration.test_semantic_acceptance
```

PR41 source checks exercise the real foundation/names/type APIs. The full
compiler, target execution and `test_oracle_precision` are outside this PR's
checkout and remain integration evidence for the root agent. Native packaging,
platform verification and human/tutor approvals remain separate gates.

Local verification in `coco-pr-41` at base `36edbcc`, macOS arm64, Python 3.14.0:
176 focused tests and 539 full source tests passed. The bounds matrix includes
126 seed/mode/limit combinations, with exact observed steps and loop iterations;
the coverage smoke range adds 120 complete programs in both numeric modes, and
the mutation suite adds 72 isolated faults across six families. Compileall,
`git diff --check`, and the existing P1 CLI black-box harness (10/10) passed.
No target/backend execution is claimed by those checks.
