# P2 source audit and 500 complete-system regressions — 24 October 2026

This review starts from main `3e44bdb281523e87b0015b5fde5cd9115a7c7717`
(PR #45). It covers the source pipeline for Parts 2a, 2b, 3a and 3b,
including actual compilation and execution of generated targets. It does not
certify a grade, a packaged SPL executable, team approval or submission.

## Course evidence checked

The private originals were inspected as rendered pages, including their colour
annotations: Syntax pp. 1–3, 2a pp. 1–4, 2b pp. 1–4, 3a pp. 1–7 and 3b
pp. 1–3. Text extraction alone was insufficient: the 2a extraction contains
only page markers. The duplicate 2a PDF is byte-identical. Private PDFs,
rendered pages and announcement text are deliberately not source assets.
The companion [source fingerprint record](P2_SPEC_SOURCE_FINGERPRINTS.json)
identifies exactly which local inputs were available for this review.

All `assoument1.txt` through `assoument13.txt` were inspected. File 6 is empty;
it provides no additional instruction. Duplicates were not treated as new
policy. Relevant announcements include:

| Announcement | Consequence for this review |
| --- | --- |
| A13/A16/A19 | Group participation, grammar and names/scopes remain applicable. Tests do not replace personal participation. |
| A21 (in files 4 and 7) | Lookup cannot cross sideways into siblings or cousins. Equal scope depth is not equal scope identity. |
| A23 (including file 8) | Generate compliant and intentionally faulty inputs; `$` is EOF notation only. Tutors run the supplied executable without rebuilding it. Source testing is not package evidence. |
| A24 | Parts 2a/2b belong to P2; P1 success does not establish semantic correctness. |
| A27/A28/A29 | First Class includes 2a, 2b, 3a and 3b with executable target correctness, up to six points. P1 is not re-assessed. |
| A33 | Final date 25 October; category/ZIP awareness declarations require actual personal signatures. Native files, final manual and upload remain release work. |

## Requirement review

The original **38 IDs** and **E01–E10 meanings** in
[requirements.json](../../tests/fixtures/codegen/requirements.json) remain intact.
Existing semantic/target acceptance manifests remain authoritative baseline
coverage. The new [500-case inventory](../../tests/fixtures/system500/index.json)
adds case-level IDs, source fingerprints, expectations and those same IDs.
Mapping a requirement records relevant evidence; it does not turn a proposed
policy into a confirmed course rule.

| Sheet / rules | Source implementation inspected | Evidence and conclusion |
| --- | --- | --- |
| Syntax pp. 1–3: separators, exact lexical forms, productions, EOF notation, original node IDs and XML links | `lexer.py`, `parser.py`, `tree.py`, `tree_reader.py`, `xml_writer.py` | Existing P1 suite retained; SYS frontend negatives, bare `#`/prefix names, XML identity and deep production cases. Found and fixed recursion-limit rejection described below. |
| 2a pp. 1–4: scope identity, nearest ancestor, no sideways search | `semantic_model.py`, `name_analysis.py` | Existing N01–N03 evidence plus sibling-local and parent/grandparent capture execution; scope violations checked inside uncalled bodies at depths 0–4. |
| 2a: duplicate locals/formals, own-parameter masking, unique function names/no overload | `name_analysis.py` | N04/N05/N07 negatives assert the specific diagnostic. Same-spelling declarations in distinct legitimate scopes execute correctly. |
| 2a: immediate-F_DECL calls, no recursion, consistent unique internal naming | `name_analysis.py`, `function_templates.py`, `call_expansion.py` | N06/N08/N09/N10: reject self/sibling/grandchild calls; accept same-spelling strict-child functions and fresh repeated expansions. Original XML spellings/IDs remain unchanged; renaming uses semantic side maps. |
| 2b pp. 1–4: postorder attributes, pre-known signatures, numeric/procedure contexts, every production/body/return | `type_analysis.py`, `semantic_model.py` | Existing T01–T10 assertions retained. SYS rejects void calls in assignment, print, argument, arithmetic, return and Boolean/loop terms, and num calls as instructions; includes uncalled nested bodies. |
| 2b: global mod/div and decimal/mod prohibitions | `numeric_policy.py`, `type_analysis.py` | Operators/NUM tokens anywhere in the whole tree count, including unused returns. Exact mandated mod/div message checked. String/comment text containing `div`, `mod` or decimal-looking text does not count. |
| 3a pp. 1–7: ALGO order, print, nop/comment, assignment, all arithmetic, one numeric mode | `codegen.py`, `codegen_ir.py`, `target_writer.py` | G01–G06: exact runtime stdout, signed remainder, self-reading assignment, nested operands and fractional division of integer-looking NUM tokens. All targets pass structural inspection and native compilation/execution. |
| 3a: Boolean composition, true/false control transfer, all four loop forms | `boolean_codegen.py`, `codegen.py`, `target_writer.py` | G07–G10: complete and/or truth tables with not, both branch arms, pre/post while/until, zero/one/many iterations and nested control flow. Executable target inspection rejects forbidden ELSE/composition and invalid labels/storage. |
| 3b pp. 1–3: code mine before main, child-before-parent templates, INPUT traversal and formal/actual transfer | `function_templates.py`, `call_expansion.py`, `inlining.py`, `target_writer.py` | F01–F04: inactive unused functions, whole TERM actuals, ordered captures before later side effects, zero/multiple actuals and deeply nested child templates. D02/D04 interpretations remain explicit below. |
| 3b: void/num expansion, return continuations, fresh labels/temporaries/locals/formals, ancestor references | Same template/inlining modules plus `codegen_ir.py` | F05–F08: repeated loop-bearing calls, nested returns, current-parent writes, grandparent/global captures and same-spelling distinct functions. No runtime SPL functions or stack are substituted for required inlining. |
| Full command: failure phases and publication | `compiler.py`, `cli.py`, `diagnostics.py` | Existing driver/IO tests retained; SYS adds fresh and stale-output negatives, success→failure→success, source preservation, direct/relative/hard-link aliases and XML re-compilation. |

The explanatory target algorithms allow implementation choices; exact temporary
spellings, forward-label ordering or comment formatting are not treated as a
required textual snapshot. Generated programs must retain their behavior and
required structural constraints. All mutable state stays local to a compile.

## Confirmed fix

The original parser uses Python call frames for nested grammar productions.
A valid `print(neg(...))` expression nested 1,100 levels reaches Python's default
recursion limit and becomes an internal failure instead of compiling. The SPL
grammar specifies no such nesting bound. Existing backend passes already use
explicit work stacks, so the parser was the remaining failure here.

The parser now suspends child productions as generators and drives them with
an explicit stack. It retains the same predictive grammar, lookahead, public
`parse(tokens, tree, path)` API, allocation order, token spellings and errors.
It neither installs another parser nor changes the process recursion limit.
Suspended generators close promptly on a syntax error. No resource-size rule
is added to SPL.

A temporary comparison against the exact base parser produced identical full
tree records or errors on 147 lexable generated/mutated programs; another 53
mutations failed lexing before either parser. The existing 28 focused parser/
pipeline tests also passed. SYS0471–SYS0500 permanently exercise six deep
shapes at five depths: TERM, BOOL, branch, post-until, nested function bodies
and nested actual calls. Each successful target is compiled and executed.

## The additional 500 tests

Each case is a separate discoverable `unittest` method named with its stable
SYS ID. This is not one test reporting 500 subtests. The factories enforce 500
unique IDs and 500 unique complete input sources, with explicit family counts.
The inventory must match the factories before the suite imports successfully.
Expectations use algebra, truth tables and written state transitions; neither
the generated target nor the existing reference evaluator supplies the answer.

| IDs | Family | Count |
| --- | --- | ---: |
| SYS0001–SYS0050 | Signed/nested arithmetic, assignment, output, inert instructions | 50 |
| SYS0051–SYS0100 | Comparisons, full and/or truth tables, not and branch selection | 50 |
| SYS0101–SYS0150 | Four loop forms, zero/one/many and nested control flow | 50 |
| SYS0151–SYS0240 | Arguments, side effects, repeated calls, captures, returns, inactive templates | 90 |
| SYS0241–SYS0270 | Legal lexical scopes and distinct declaration identities | 30 |
| SYS0271–SYS0360 | Specific name/type violations at five uncalled-body nesting depths | 90 |
| SYS0361–SYS0390 | Global numeric conflicts and mode-selection boundaries | 30 |
| SYS0391–SYS0420 | P1 lexical and syntax rejection boundaries / line offsets | 30 |
| SYS0421–SYS0470 | Recovery, aliases, XML and source/output preservation | 50 |
| SYS0471–SYS0500 | Deep valid grammar and full native target execution | 30 |

Valid cases start a fresh interpreter at the public `spl_frontend` module in a
working directory with spaces, normally with no CLI arguments (`SPL.txt`).
They require both outputs, validate XML, inspect executable target structure,
compile C++ with warnings enabled, execute with a timeout and compare exact
stdout and status. A missing C++ compiler is a failure, not a skip.

Invalid cases assert the intended public status/code, real path and source
position, no traceback, unchanged source and absence of both stale/partial
outputs. Semantic/codegen negatives first pass the actual lexer/parser, so a
syntax failure cannot masquerade as a successful semantic rejection test.
Recovery cases run valid→invalid→valid in the same directory and execute the
recovered target. Alias cases preserve source and prior outputs on preflight
rejection. XML cases compare exact target source and unchanged node records
when compiling the emitted XML back through the real semantic/backend API.

Failure evidence goes under ignored `build/system500-failures/SYSxxxx/`:
input/output files, expectation metadata, stage commands/status/stdout/stderr
and an individual unittest reproduction command. Use:

```sh
# All existing and new tests, normal discovery:
PYTHONPATH=src python3 -m unittest discover -s tests -v
# Only the 500, bounded parallel execution and per-case JSON results:
python3 tools/run_system_500.py --workers 4 --report build/system500-report.json
# Reproduce one case:
PYTHONPATH=src python3 -m unittest tests.integration.test_system_500.CompleteSystem500Tests.test_SYS0471_deep -v
# After intentional changes to the factories:
python3 tools/run_system_500.py --write-inventory
```

Do not execute the historical suite in threads alongside these methods:
some historical tests temporarily change the process working directory.
The optional runner threads only this isolated new class. Normal discovery
remains serial and requires no custom runner.

## Interpretation and release limits

[D01–D08](05_SHARED_INTERFACES.md#tutor-decisions) remain pending actual tutor
confirmation. This audit does not manufacture an answer: C++/`program.cpp`,
formal=captured-actual, explicit true/false jumps, exact arity/left-to-right/
short-circuit policy, numeric/output representation, namespace/return scope,
extra output schemas and tutor platform/launch details retain their recorded
status. Tests involving them document current behavior rather than new rules.
The explicit global numeric conflicts and scope restrictions are confirmed
independently of those proposals.

Course sources do not define arbitrary-precision numeric storage, overflow,
underflow or division-by-zero runtime policy. The executable corpus uses
initialized bounded values and terminating loops. It does not claim all
possible programs, native numeric values or machine resource sizes are covered.

Issues #35 (exact native compiler artifacts/platform validation) and #36
(final launch manual, both actual personal declarations and verified upload)
remain open and outside this request. Source-to-C++ execution is essential P2
verification; it is not a packaged compiler release. Neither the existing full
P1 mark nor 500 more passing tests guarantees a six-point assessment result.

## Recorded validation

Local environment: macOS 27.0 arm64, Python 3.14.0, Apple clang 21.0.0.

| Check | Actual result |
| --- | --- |
| Full normal unittest discovery | **1,188 passed**, 386.681 seconds; original 688 retained, 500 added |
| Dedicated 500-case runner, four workers | **500/500 passed**, 74.234 seconds; 360 cases compile/run native targets, 140 reject invalid programs |
| Final stricter path/line-position and recovery checks | **165/165 passed**, 7.684 seconds |
| Public CLI black-box harness | **10/10 passed** |
| `compileall` for src/tests/tools | Passed |
| Python 3.11 grammar parsing | All 92 Python files accepted; not a Python 3.11 runtime result |
| `actionlint` and whitespace checks | Passed |
| Failure-harness sensitivity probes | Wrong stdout, wrong phase and timeout all rejected; retained stage evidence checked |

The dedicated runner's 360 execution cases include 25 valid→invalid→valid
recovery sequences; all 165 negative compile attempts are checked for their
intended failure. Per-case reports are reproducible with the commands above
and remain ignored build outputs. Full-suite discovery reports no skips.

Local results must not be presented as Linux/Windows/Python 3.11 runtime
passes. A GitHub Actions startup failure with zero jobs is unverified hosted
coverage, regardless of local results. Hosted status is recorded separately in
the PR. No independent member approval is claimed by this self-review.
