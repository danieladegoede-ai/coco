# Expanded P2 source audit — 25 October 2026

> Release instruction, 25 October: the Speaker finalized D01-D08 without
> tutor consultation and appointed this AI as main technical reviewer. Use
> [the final release contract](../../release/P2_RELEASE_DECISIONS.md). The dated
> allocations/proposals below are historical and add no consultation or
> named-peer technical-review gate. A33 personal signatures/upload remain real
> personal actions.

The expanded audit starts at merged main
`3b46695aad7274fde1f5b801415714cee31c43c5` (PR #46). It retains the previous
1,188 tests, adds **5,000 edge-matrix methods** and **ten numeric-boundary
methods**, and checks that normal discovery contains exactly **6,198 unique
method IDs**. All those methods were executed, with no skips, in the validation
partitions below. A larger count is evidence about the specified matrix, not
proof of every possible program or a promised assessment mark.

## Course evidence and audit scope

All 19 private inputs in
[P2_SPEC_SOURCE_FINGERPRINTS.json](P2_SPEC_SOURCE_FINGERPRINTS.json) still match
the earlier audit byte for byte. No newer numbered announcement file was found.
The previous visual inspection of all 21 Syntax/2a/2b/3a/3b pages, including
colour annotations and the scanned 2a pages, therefore remains applicable.
The [earlier audit](P2_SPEC_AUDIT_20261024.md) records those page-level sources,
announcement meanings and duplicate/empty inputs; announcement file 6 is empty.
Private PDFs, photos and announcement text are not copied into this PR.

This pass rechecks the actual source interfaces and their integration:

| Boundary | Confirmed source requirement / implementation review | Expanded evidence |
| --- | --- | --- |
| Loading/lexing | ASCII input, exact token forms, separators including the final token, internal EOF only; no source `$` | 800 lexical negatives in four positions and five layouts, source-loader non-ASCII cases, exact fault positions, paired valid sources |
| Parsing/XML | Same predictive grammar, nullable lists, whole-input acceptance, original token spellings/IDs/parent and child links | 450 grammar negatives at three enclosing depths; all successful cases compare source token positions, fresh parser records and emitted XML; previous deep nesting regressions retained |
| Scopes/names (2a) | One P scope identity per body; nearest current/ancestor variable, no sideways cousin/sibling search; duplicate domains, parameter masking, direct-F_DECL calls, no overload/recursion, declaration-based internal names | 350 legal scope cases; 900 name/type negatives at six uncalled-body depths; bare/prefix/long names, 30+ declarations, same spelling in legal separate scopes, explicit cousin/global counterexamples |
| Attributes/types (2b) | Declaration signatures seeded before body checks; bottom-up attributes; all bodies/returns and productions traversed; numeric/procedure call contexts | Grammar-valid negative inputs plus independently checked positive partners; invalid calls in assignment/print/arithmetic/arguments/returns/comparisons/loops; original type/model invariants retained |
| Numeric policy | Both mod/div anywhere reject with the exact required message; any mod plus decimal NUM rejects; operator-looking string text does not count | 200 mode/conflict cases across uncalled nesting/layouts; integer sign/remainder cases; ten safe int32/binary32 boundary executions |
| ALGO/terms/output (3a) | Instruction order, RHS before store, all six operations, inert nop/comment, exact string/numeric print and whole-program storage mode | 600 expression/assignment cases; independent integer algebra and exact half-division expectations; executable target structure, C++ compilation and runtime stdout checks |
| Branches/Booleans/loops (3a) | Primitive comparisons/labels/gotos, explicit true/false transfer, no executable ELSE or Boolean composition; all four loop forms | 450 Boolean cases with observable call traces and independent short-circuit truth oracle; 450 loops with zero/one/many iterations, condition side effects, nested controls and repeated calls |
| Templates/inlining (3b) | Inactive code mine before main; child-before-parent construction; recursive INPUT order; capture actuals before formal copies; correct return continuation; fresh storage/labels and current ancestor captures | 650 call cases, up to ten actuals, nested actuals/returns, earlier-argument capture, repeated parent/child calls, inactive functions and root/parent/grandparent bindings; original IR/template unit checks retained |
| Public CLI/public APIs | Default and explicit source paths; expected phase/status; silent library errors; validated final output; source-preserving alias checks before cleanup | 150 lifecycle cases: valid→invalid→valid across five failure phases, spaces/Unicode/nested/long filenames, hardlinks/symlinks, output-output alias, unrelated symlink destinations, missing/directory/empty input, XML corruption, repeat determinism and frontend-only boundary |
| Failure evidence and test execution | Fresh bounded processes, separate compiler/native/run outcomes, reproducible failures, no false pass for skipped native execution | Five deliberately faulty harness probes failed; exact discovery/partition equality checked; CI uses four disjoint edge shards instead of dropping tests |

The original **38 planning IDs** and **E01–E10 meanings** are unchanged. The
[edge inventory](../../tests/fixtures/edge5000/index.jsonl) records every source
hash, scenario/layout, expected output or error/code/position, positive-partner
hash, profile, relevant requirement IDs and provisional policy. The requirement
traceability table below is generated from those actual tags. Tags identify
relevant evidence; one case does not establish every aspect of a tagged rule.

## What changed, and findings

The expanded matrix found **no additional confirmed compiler defect** in the
executed domain. There is consequently no speculative production-code rewrite.
The earlier explicit-stack parser fix is retained and passed the entire old
suite, including its deep-source execution cases.

The audit closed test-coverage gaps: exact error positions across CR, LF, CRLF
and mixed separators; side-effect traces in Boolean evaluation; six nesting
levels of uncalled semantic faults; cousin lookup versus global fallback;
wide actual/declaration lists; input/output/output alias relations; explicit
source path variants; XML corruption and unchanged original node identities.
The ten extra boundary tests distinguish binary32 storage from binary64 at
2^24, exercise safe INT_MIN/INT_MAX operations, signed remainder and fractional
equality. They assert the currently implemented D05 target representation;
they do not add a new grammar or overflow rule.

No requested work was replaced with a test-count-only loop: the 5,000 are
separate unittest methods and distinct source hashes, with no overlap with the
previous 500 SYS sources. The matrix intentionally crosses structural/value
conditions with five layouts. It represents 5,000 edge inputs, not 5,000
different productions. Algebra, written state transitions and the small
independent Boolean/trace evaluator produce expectations; production IR,
generated C++ and the existing reference SPL evaluator do not supply answers.

## Matrix dimensions

| Stable IDs | Family | Cases | Main axes |
| --- | --- | ---: | --- |
| EDGE00001–EDGE00600 | Arithmetic | 600 | 12 topologies × 10 signed/zero operand pairs × 5 layouts |
| EDGE00601–EDGE01050 | Booleans | 450 | 15 formulas × 6 value pairs × 5 layouts; emitted probe trace is part of stdout |
| EDGE01051–EDGE01500 | Loops | 450 | 15 control patterns × 6 iteration bounds × 5 layouts |
| EDGE01501–EDGE02150 | Calls | 650 | 26 call/capture/return scenarios × 5 argument values × 5 layouts |
| EDGE02151–EDGE02500 | Legal scopes | 350 | 14 binding/name scenarios × 5 values × 5 layouts |
| EDGE02501–EDGE03300 | Lexical faults | 800 | 40 faults × 4 source contexts × 5 layouts |
| EDGE03301–EDGE03750 | Syntax faults | 450 | 30 grammar boundaries × 3 enclosing depths × 5 layouts |
| EDGE03751–EDGE04650 | Semantic faults | 900 | 30 name/type violations × 6 enclosing depths × 5 layouts |
| EDGE04651–EDGE04850 | Numeric policy | 200 | 10 conflict/mode scenarios × 4 depth/value variants × 5 layouts |
| EDGE04851–EDGE05000 | Lifecycle/APIs | 150 | Recovery, aliases, IO, imported XML, determinism and explicit-path variants |

A rejection case checks its intended status/code, exact independent path/line/
column, unchanged input and removal of stale XML/C++. Semantic/codegen faults
first pass the actual lexer/parser. All 2,310 rejection-only cases have a
positive partner accepted by the full library pipeline. Whole-tree faults in
unused bodies must still fail; they are not hidden behind reachability.

Every successful matrix case uses the actual public module as a fresh CLI
subprocess, then native C++ compilation/execution and exact stdout/status
comparison. Successful ordinary cases also compare every token position with
an independent splitter/CRLF position oracle, validate XML, compare exact fresh
parser/XML node records, recompile imported XML through real names/types/
inlining, and check deterministic source plus distinct internal symbol names.
Recovery cases execute the recovered target. Native work is required rather
than silently skipped when no C++ compiler is available.

## Actual execution evidence

Local toolchain: **macOS 27.0 arm64, Python 3.14.0, Apple clang 21.0.0**.
Separate processes were used for the old serial suite and threaded new matrix;
no historical test that changes cwd was threaded with other cases.

| Check | Result |
| --- | --- |
| Retained baseline, before the ten new boundary methods | **1,188 passed**, 521.411 s, zero skips |
| Complete edge matrix, six workers | **5,000/5,000 passed**, 429.095 s, zero skips |
| Extra native numeric-boundary methods | **10/10 passed**, 7.622 s |
| Final strengthened explicit-path/XML cases | **30/30 passed**, 4.575 s |
| Final explicit-path UTF-8 subprocess protocol checks | **25/25 passed**, 4.146 s |
| Public source CLI black-box harness | **10/10 passed** |
| Preflight (not additional counted tests) | All 5,000 API/expected-phase checks passed |
| Failure sensitivity (not additional counted tests) | Wrong stdout, phase, position, positive partner and timeout were rejected with retained evidence |
| Discovery/CI partition proof | Exactly 6,198 unique discovered IDs = 1,188 retained + 5,000 edges + 10 boundaries; four disjoint 1,250-case edge shards cover all 5,000 |
| Static checks | compileall, Python 3.11 grammar parsing of all 98 Python files, actionlint and whitespace checks passed |

The 5,000-case run recorded **5,195 real compiler subprocess invocations**,
**2,690 C++ compilations and executions**, **2,310 positive-partner checks** and
**2,650 API/XML checks**. The ten new boundary methods add ten further native
compilations/executions. These counters describe operations, not extra unittest
methods; recovery/alias scenarios intentionally invoke the compiler repeatedly.
Full per-case reports remain in ignored `build/edge5000-*.json`, with failed
case inputs/expectations/stage commands/statuses/logs and reproduction commands
under `build/edge5000-failures/`. No production failure artifacts were produced;
temporary deliberately faulty harness-probe artifacts were inspected then removed.

Reproduce with Python >=3.11 and a C++ compiler:

```sh
# All current 6,198 methods: baseline serially, edges in bounded threads.
python3 tools/run_edge_5000.py --suite all --workers 6
# Edges only, or one exact failing ID:
python3 tools/run_edge_5000.py --suite edges --workers 6
python3 tools/run_edge_5000.py --ids EDGE01501
# Ordinary discovery also includes every method, but runs serially:
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Remaining policy/platform/release gates

The audit does not supply missing tutor answers. [D01–D08](05_SHARED_INTERFACES.md#tutor-decisions)
remain explicit proposals: target dialect/filename/command, formal/actual
wording, Boolean jump interpretation, arity/evaluation order/short circuit,
numeric/output representation, namespaces/return scope, extra output schemas
and tutor OS/CPU/release details. Confirmed lookup and global numeric rules are
checked independently of those questions.

The corpus uses initialized values and terminating bounded loops. It does not
establish arbitrary precision, undefined overflow, division by zero, unbounded
resources or every possible program. Production inlining has an existing
**1,000,000-instruction resource guard**; the original template/inlining unit
tests check its failure behavior with a reduced injected budget. This is a
resource limit, not a newly invented SPL syntax/type prohibition. Raw imported
XML validation establishes the documented flat schema/graph; source lexical
validation still belongs to the source pipeline.

Local passes do not establish Python 3.11 runtime, Linux/Windows or the exact
packaged compiler. Symlink cases need a filesystem/account that permits their
creation; an unavailable native compiler/filesystem capability is not silently
presented as a successful execution. Hosted CI has previously failed before
starting jobs; the new PR records its actual current status separately.

Native compiler packaging **#35** and final manual, real personal declarations,
group approval and verified upload **#36** remain open and excluded, as requested.
The source audit does not claim those release actions, an independent human
approval, or guaranteed full marks. This was a direct source/test self-review;
no new delegated review was requested for this task.

## Original requirement traceability

The following summary is generated from the exact committed 5,000-case
inventory. Existing evidence in `tests/fixtures/codegen/requirements.json` and
the earlier SYS corpus is retained alongside it.

| ID | Original planning requirement | New cases / relevant families | Example IDs |
| --- | --- | --- | --- |
| N01 | Create a scope hierarchy by nested P/function bodies. Track scope identity as well as depth. | 1000 (calls: 650, scopes: 350) | EDGE01501, EDGE02001, EDGE02500 |
| N02 | A variable use must resolve in its current scope or an ancestor; choose the nearest matching declaration. | 1060 (calls: 650, scopes: 350, semantic: 60) | EDGE01501, EDGE02031, EDGE04555 |
| N03 | Never search sideways into sibling functions or their descendants. [A21] | 110 (scopes: 50, semantic: 60) | EDGE01656, EDGE03811, EDGE04565 |
| N04 | Reject duplicate variable names in one declaration scope, including duplicate parameters. | 120 (semantic: 120) | EDGE03751, EDGE04201, EDGE04520 |
| N05 | A function body local may not mask a parameter of that same function. | 60 (semantic: 60) | EDGE03771, EDGE04221, EDGE04530 |
| N06 | Calls from a P algorithm may target only functions declared in the immediate F_DECL of that P. | 995 (calls: 650, scopes: 225, semantic: 120) | EDGE01501, EDGE02068, EDGE04585 |
| N07 | Function names in the applicable F_DECL must be unique; no overloading. | 115 (scopes: 25, semantic: 90) | EDGE01691, EDGE04083, EDGE04545 |
| N08 | No direct or indirect recursion. Strict child-only visibility is the primary rule. | 115 (scopes: 25, semantic: 90) | EDGE01691, EDGE04118, EDGE04585 |
| N09 | Consistently rename every declaration and use: same entity, same internal name; different entities, different internal names. | 1100 (calls: 650, lifecycle: 100, scopes: 350) | EDGE01501, EDGE02051, EDGE04975 |
| N10 | Reject rule violations with appropriate messages; accept compliant programs without name errors. | 910 (lifecycle: 50, scopes: 350, semantic: 510) | EDGE01631, EDGE03921, EDGE05000 |
| T01 | Attributes and symbols | 700 (arithmetic: 600, lifecycle: 100) | EDGE00001, EDGE00351, EDGE04975 |
| T02 | Variables and functions | 660 (arithmetic: 600, semantic: 60) | EDGE00001, EDGE00331, EDGE04650 |
| T03 | Calls and INPUT | 1150 (booleans: 450, calls: 650, numeric: 20, semantic: 30) | EDGE00601, EDGE01626, EDGE04850 |
| T04 | Call context | 1490 (booleans: 450, calls: 650, semantic: 390) | EDGE00601, EDGE01936, EDGE04650 |
| T05 | Assignment / leaves | 650 (arithmetic: 600, numeric: 20, semantic: 30) | EDGE00001, EDGE00326, EDGE04850 |
| T06 | Arithmetic | 890 (arithmetic: 600, numeric: 200, semantic: 90) | EDGE00001, EDGE00446, EDGE04850 |
| T07 | Booleans / control | 1050 (booleans: 450, loops: 450, semantic: 150) | EDGE00601, EDGE01126, EDGE04635 |
| T08 | Output / simple instructions | 630 (arithmetic: 600, semantic: 30) | EDGE00001, EDGE00316, EDGE04595 |
| T09 | Structural productions | 1800 (lifecycle: 100, scopes: 350, semantic: 900, syntax: 450) | EDGE01631, EDGE03851, EDGE04975 |
| T10 | Complete traversal | 1910 (lexical: 800, lifecycle: 50, numeric: 160, semantic: 900) | EDGE02501, EDGE03906, EDGE05000 |
| G01 | Preserve ALGO instruction order; empty ALGO terminates cleanly. Emit readable statements and newlines. | 2450 (arithmetic: 600, lexical: 800, lifecycle: 150, loops: 450, syntax: 450) | EDGE00001, EDGE02676, EDGE05000 |
| G02 | print STRING writes the string; print(TERM) computes into a temporary and writes its value. | 620 (arithmetic: 600, numeric: 20) | EDGE00001, EDGE00311, EDGE04849 |
| G03 | nop becomes a harmless comment; comment STRING becomes a target comment. | 620 (arithmetic: 600, numeric: 20) | EDGE00001, EDGE00311, EDGE04849 |
| G04 | Assignment computes the TERM first, then stores it in the renamed target variable. | 620 (arithmetic: 600, numeric: 20) | EDGE00001, EDGE00311, EDGE04850 |
| G05 | NAME and NUM terms copy into a result location. Operators map to %, /, +, -, *, and unary -. | 620 (arithmetic: 600, numeric: 20) | EDGE00001, EDGE00311, EDGE04850 |
| G06 | Every generated variable has the selected whole-program int or float type. | 800 (arithmetic: 600, numeric: 200) | EDGE00001, EDGE00401, EDGE04850 |
| G07 | Translate branches using labels and goto; no executable ELSE command. | 900 (booleans: 450, loops: 450) | EDGE00601, EDGE01051, EDGE01500 |
| G08 | Lower Boolean composition into jumps, not target and/or/not or &&////! expressions. | 900 (booleans: 450, loops: 450) | EDGE00601, EDGE01051, EDGE01500 |
| G09 | Support pre-test while, pre-test until, post-test while and post-test until. | 450 (loops: 450) | EDGE01051, EDGE01276, EDGE01500 |
| G10 | Use resolved internal names, fresh temporaries and unique labels throughout. | 900 (booleans: 450, loops: 450) | EDGE00601, EDGE01051, EDGE01500 |
| F01 | Emit one root main, the needed declarations and return 0. Nested P bodies supply templates, not nested main definitions. | 750 (calls: 650, lifecycle: 100) | EDGE01501, EDGE02016, EDGE04975 |
| F02 | Build reusable, non-executable templates keyed by resolved function symbol. Retain the code-mine concept in the generated output. | 650 (calls: 650) | EDGE01501, EDGE01966, EDGE02430 |
| F03 | Walk the recursive INPUT chain to count ordered TERM arguments. | 1100 (booleans: 450, calls: 650) | EDGE00601, EDGE01601, EDGE02430 |
| F04 | Evaluate actual arguments into fresh capture temporaries before populating the cloned formal parameters. | 1025 (booleans: 450, calls: 575) | EDGE00601, EDGE01573, EDGE02430 |
| F05 | Inline void bodies for instruction calls; inline num bodies and copy the return result into the caller continuation variable. | 1720 (booleans: 450, calls: 650, lifecycle: 150, loops: 450, numeric: 20) | EDGE00601, EDGE01461, EDGE05000 |
| F06 | Expand a child function inside its parent template before the parent is inserted into main. | 175 (calls: 175) | EDGE01541, EDGE01973, EDGE02420 |
| F07 | Each expansion has unique labels, temporaries, local/formal storage and return storage. | 125 (calls: 125) | EDGE01526, EDGE01958, EDGE02430 |
| F08 | Captured ancestor variables retain the correct binding under expansion. | 400 (calls: 175, scopes: 225) | EDGE01541, EDGE02056, EDGE02500 |
