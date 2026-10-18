# u21434019 / Cherise / CheriseHeyl: target IR, arithmetic, Boolean/control-flow generation and executable verification

Updated 18 October 2026. Primary issues: **#26, #27, #28, #34**. This packet contains
the detailed issue requirements locally so your AI can work without this
conversation. Read live issues/PRs for subsequent changes and actual status.
Requirements below are task checklists, not assertions that work is complete.

## Copy this starting prompt to your AI

```text
You are helping Cherise (u21434019, GitHub CheriseHeyl) on Group 2 COS341
2026 P2, targeting 1st Class. Read root AGENTS.md, agent_tasks/p2/00_START_HERE.md,
agent_tasks/p2/30_u21434019_codegen_verification.md, the shared interfaces and handoff guide,
then inspect the live repository and my issues: #26, #27, #28, #34.
Implement my selected owned issue; if none was selected, choose the earliest
useful owned task after checking actual dependencies and existing PRs. Explain
the branch/API boundary and continue through implementation, meaningful tests,
documentation and a focused reviewable PR. Preserve other members' work and
the full-marks P1 frontend. Do not recreate pending implementations, invent
tutor decisions, claim unrun tests passed, or sign/upload on anyone's behalf.
If an integration dependency is pending, build independent fixtures or use an
explicit stacked branch and state what remains blocked.
```

## Read and inspect before changing files

Read [start guide](00_START_HERE.md), [shared interfaces](05_SHARED_INTERFACES.md),
[acceptance/handoff](90_HANDOFF_AND_ACCEPTANCE.md), [root rules](../../AGENTS.md),
the relevant official 2026 sheets/announcements, and your actual source/tests.
Record branch/base and inspect git status. Pending code is in #37/#38; the
main CLI stays frontend-only until #31. Use Python >=3.11.

## Recommended work order and independent start

1. Begin #26 with foundation/checked-model fixtures on an explicit base
   containing #22. Coordinate structural IR references, allocators and clone/
   remap with Michele before downstream code depends on incidental formatting.
2. Render and actually compile/run the minimal skeleton. Isolate D01's target
   dialect/filename proposal. Hoist all declarations and validate labels early.
3. Build #27 terms/simple instructions against Kuda's one numeric mode. Supply
   a call hook for Michele; do not write a competing inliner.
4. Build #28 with the emit_bool(B,T,F) invariant. Prove truth tables and all
   four loops by target execution, not by copying implicit-fallthrough hints.
   Keep D03/D04 evaluation proposals documented for consultation.
5. Scaffold #34's timeout/log/artifact harness and handwritten expected outputs
   now. Add each real backend feature as it lands, then integrate #32/#33.
   Give Michele a runnable source-based corpus; package reruns happen in #35.

## Ownership and coordination boundaries

- Own codegen_ir.py, target_writer.py, terms/simple-instruction codegen.py,
  boolean_codegen.py and the specified verification harness/fixtures.
- The parser remains your P1 module but should not be rewritten for semantic
  work. Reuse concrete-tree helpers and resolved declaration IDs.
- Work with Michele on the call/continuation hook and shared codegen dispatch.
  IR changes must preserve safe structural clone/remap, fresh labels/storage
  and target declarations introduced by inlining.
- Consume CheckedProgram and Kuda's NumericMode; no independent mode guess,
  raw spelling lookup or permissive path around a failed semantic pass.
- The executable code uses comparison/goto lowering; no ELSE or &&/||/!
  composition standing in for the required translation. Ignore comments and
  strings when verifying structural vocabulary.
- Review #24 numeric facts, #30 inlining, #32 oracle and #35 native artifacts;
  do not count an oracle that mirrors your backend as independent evidence.

## Concrete anchors your implementation must distinguish

- Minimal target: exactly one main, correctly typed declarations, return 0,
  legal empty/end labels and no accidentally executable code-mine body.
- div(5,2)=2.5 even when source literals are integer-looking; mod(5,2)=1.
  Compute RHS before storing so x=add(x,1) reads the original x correctly.
- `: : if or ( not ( eq ( 1 1 ) ) eq ( 1 2 ) ) then { print "bad" ; }
  else { print "ok" ; } ; ` must produce exactly `ok`. Test the full truth
  tables and nested not/and/or, not only this one false-fall-through case.
- Pre-while and pre-until can execute zero times; post-while and post-until
  execute their bodies at least once. Test both initial outcomes and bounded
  repeated iterations with timeouts.
- Repeated inlined loop functions need disjoint label definitions and matching
  remapped gotos. Non-executed Boolean operands must preserve side-effect
  behavior under the recorded short-circuit policy.
- A target that compiles but prints the wrong result must fail #34. Save source,
  generated target, compiler/runtime logs, command, seed and expected events.

## Detailed owned issues

The requirements below are copied from the live assigned issue snapshot.
The linked issue remains the live progress/review record. Proposed paths
and interfaces must be reconciled with the actual branch; do not invent
missing implementations or cross-owner approvals. Retain real dependency
gates even when independent work can begin.

### [#26: [P2-06][u21434019] Build target instruction model, fresh-name allocator and executable program skeleton](https://github.com/RudolphLamp/coco/issues/26)

**Reviewer:** `michey-n`. Review does not transfer implementation ownership.

#### Outcome

Create the small structured target representation used by algorithm generation and inlining, and render one valid target program with one main. Use the agreed C/C++ dialect; the sheets' iostream/cout examples require C++ unless the tutor specifies an alternative.

#### Dependencies and independent start

Complete the interfaces/results in [P2-01 / #21](https://github.com/RudolphLamp/coco/issues/21), [P2-02 / #22](https://github.com/RudolphLamp/coco/issues/22) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/codegen_ir.py`
- `src/spl_frontend/target_writer.py`
- `tests/unit/test_codegen_ir.py`
- `tests/unit/test_target_writer.py`
- `tests/integration/test_target_skeleton.py`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Define typed instruction/operand/label/symbol references rather than backend-wide raw string substitution.
- Provide per-compilation deterministic fresh IDs for labels, temporaries and expansion storage; disjoint namespaces prevent collisions with renamed user symbols.
- Provide one target-program declaration section using the numeric mode from the checked program; include captures/return temporaries introduced later.
- Emit the agreed header, exactly one int main, executable statement section and final return 0. Nested P bodies must not render their own main.
- Hoist plain declarations before jump-controlled statements and render assignments separately so C++ gotos do not cross initialized declarations.
- Ensure every rendered label is followed by a legal statement, including empty/end labels. Verify unique definitions and known goto targets.
- Support a non-executable code-mine section for function templates. Render its contents safely without nested block comments accidentally ending the outer comment.
- Implement deterministic readable target serialization with semicolons/newlines, supported string/comment escaping and no raw SPL # identifiers in executable target code.
- Expose construction/clone/remap operations needed by arithmetic, Boolean lowering and the inliner; keep this issue free of full call expansion logic.

#### Required tests and evidence

- A minimal `: : ` SPL/checked-model fixture renders target source that the chosen native target compiler accepts and runs with empty stdout.
- Exactly one main and one final return; declaration typing; deterministic generated names across fresh compilations.
- Duplicate labels, unknown goto labels and undeclared operands are caught at the agreed validation boundary.
- A label at the end of an otherwise empty block still renders compilable code.
- Template comments containing generated nop/comment annotations remain non-executable and do not break compilation.
- Clone/remap leaves string text and longer identifier spellings untouched; allocation state is not global.

#### Acceptance criteria

- Both algorithm and inlining owners can build target instructions using this public model.
- A real target-compiler smoke test passes, not just a substring snapshot.
- Program skeleton, declaration and label invariants have clear validation failures and do not depend on source spelling.

### [#27: [P2-07][u21434019] Generate executable arithmetic, assignments, output and simple instructions](https://github.com/RudolphLamp/coco/issues/27)

**Reviewer:** `Kuda21`. Review does not transfer implementation ownership.

#### Outcome

Translate every non-control, non-call algorithm/term form into executable target instructions with correct numeric behavior and instruction order. Calls plug into the agreed continuation interface owned by the inliner.

#### Dependencies and independent start

Complete the interfaces/results in [P2-05 / #24](https://github.com/RudolphLamp/coco/issues/24), [P2-06 / #26](https://github.com/RudolphLamp/coco/issues/26) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/codegen.py (terms/simple instructions)`
- `tests/unit/test_codegen_terms.py`
- `tests/integration/test_codegen_arithmetic.py`
- `tests/fixtures/codegen/arithmetic/`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Implement emit_term(term, result_location, environment), using resolved symbol references for NAME and exact valid NUM values.
- Lower binary add/sub/mul/div/mod to +, -, *, /, % with explicit operand temporaries; lower neg to unary -. Preserve evaluation order agreed in the contract.
- Use whole-program float storage for div cases, including integer-looking literals, and int storage for mod. Do not silently cast fractional results away.
- Compute assignment RHS before storing into the resolved target; correctly handle #x = add(#x,1) and nested expressions.
- Emit numeric print through a computed temporary and string print without inserting extra visible spaces/newlines. Record the output-format policy.
- Render nop and comment as non-executable comments; neither produces runtime output or changes program state.
- Iterate recursive ALGO lists in source order and handle nullable ALGO safely.
- Introduce a small emit_call/continuation hook for TERM -> CALL rather than implementing a second independent inliner.
- Keep library generation silent; return IR or structured generation errors for the driver.

#### Required tests and evidence

- Compile and execute each arithmetic operator, nested mixed arithmetic and negation with initialized variables and safe non-zero divisors.
- div(5,2) yields numeric 2.5; mod(5,2) yields 1; add/sub/mul use expected values under both selected modes.
- Assignment reads the original operand values before overwriting the destination.
- Exact string output, empty string, numeric output and consecutive print order; nop/comment alone produce empty stdout.
- Symbolically distinct same-spelling variables use the correct renamed storage in supplied scope fixtures.
- Generated target compiles without undeclared temporaries, raw # identifiers or type/operator mismatches.

#### Acceptance criteria

- Every simple instruction and all six arithmetic operators have actual compile-and-run evidence.
- Output behavior and numeric results match the language/policy rather than a test of the generator's own strings.
- The public term interface supports caller-provided result locations for later inline return values.

### [#28: [P2-08][u21434019] Implement verified Boolean jumps, branches and all four loop forms](https://github.com/RudolphLamp/coco/issues/28)

**Reviewer:** `michey-n`, with truth-table cross-check by `Kuda21`. Review does not transfer implementation ownership.

#### Outcome

Generate semantically correct control flow using comparison tests, labels and goto. The executable target must not use ELSE or target Boolean composition to avoid the translation work required by the sheet.

#### Dependencies and independent start

Complete the interfaces/results in [P2-06 / #26](https://github.com/RudolphLamp/coco/issues/26), [P2-07 / #27](https://github.com/RudolphLamp/coco/issues/27) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/boolean_codegen.py`
- `src/spl_frontend/codegen.py (control-flow dispatch only, coordinate shared file)`
- `tests/unit/test_boolean_codegen.py`
- `tests/integration/test_codegen_control_flow.py`
- `tests/fixtures/codegen/control_flow/`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Use and document emit_bool(B,T,F): execution reaches T iff B is true, otherwise F. Propose explicit true/false transfers and confirm with the tutor instead of copying implicit-fallthrough hints uncritically.
- Lower eq/larger/lesser to ==, >, < after evaluating numeric terms; use an explicit false transfer where needed.
- Lower not by swapping destinations; and by evaluating RHS only after a true LHS; or by evaluating RHS only after a false LHS. Use fresh continuation labels.
- Lower if/then/else into branch-entry labels and a shared continuation, with no executable ELSE token.
- Implement pre-test while: true -> body -> test, false -> exit; pre-test until: true -> exit, false -> body -> test.
- Implement post-test while and post-test until with one guaranteed body execution before checking the condition.
- Handle nested branches/loops, empty algorithms, labels in later inline templates and calls within conditions through the public term hook.
- Tokenize executable target code for structural checks so strings/comments mentioning else/not do not create false positives.

#### Required tests and evidence

- Execute all four truth combinations for and/or, both for not, and both outcomes of every comparison.
- Nested cases include or(not(true),false), and(not(false),true), not(and(true,false)) and not(or(false,true)); represent constants using legal comparisons.
- ` : : if or ( not ( eq ( 1 1 ) ) eq ( 1 2 ) ) then { print "bad" ; } else { print "ok" ; } ; ` must print `ok`.
- Each loop gets initially true/false conditions, zero-iteration pre-test and one-iteration post-test cases, and a terminating multi-iteration case.
- Short-circuit cases use side-effecting direct-child numeric functions after inlining integration; confirm an untaken operand does not run under the agreed semantics.
- All executable tests use timeouts; verify label uniqueness and absence of executable ELSE/&&/||/! composition.

#### Acceptance criteria

- Truth tables, nested Boolean cases and all four loop forms pass actual execution.
- The target obeys the project's restricted control-flow vocabulary and remains compilable under repeated inline cloning.
- Any deviation from a sheet hint is documented by the invariant, a concrete test and the recorded tutor decision.

### [#34: [P2-14][u21434019] Verify generated target programs with behavioral and structural acceptance tests](https://github.com/RudolphLamp/coco/issues/34)

**Reviewer:** `Kuda21`. Review does not transfer implementation ownership.

#### Outcome

Exercise the compiler as a user, compile its emitted target, run it with timeouts and compare independent expected behavior. This is the main evidence for the 1st Class goal, where tutors focus on the correctness of executable output.

#### Dependencies and independent start

Complete the interfaces/results in [P2-07 / #27](https://github.com/RudolphLamp/coco/issues/27), [P2-08 / #28](https://github.com/RudolphLamp/coco/issues/28), [P2-10 / #30](https://github.com/RudolphLamp/coco/issues/30), [P2-11 / #31](https://github.com/RudolphLamp/coco/issues/31), [P2-12 / #32](https://github.com/RudolphLamp/coco/issues/32), [P2-13 / #33](https://github.com/RudolphLamp/coco/issues/33) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `tools/test_generated_target.py`
- `tests/integration/test_executable_semantics.py`
- `tests/fixtures/codegen/acceptance/`
- `tests/fixtures/codegen/requirements.json`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Build a harness that runs source or packaged compiler in a fresh temporary directory, locates the agreed target output, invokes the agreed native target compiler and executes the result.
- Separate compiler-process status/stderr, target-compilation status/stderr and target runtime stdout/status. A target syntax failure cannot count as compiler success evidence.
- Populate a requirement-to-case matrix for all 38 planning IDs N/T/G/F, using semantic cases from [P2-13 / #33](https://github.com/RudolphLamp/coco/issues/33) and behavioral cases here without duplicating ownership of test implementations.
- Use hand-computed fixtures and the independent oracle from [P2-12 / #32](https://github.com/RudolphLamp/coco/issues/32); preserve failing source, target, commands, seed and logs.
- Check numeric operations, exact strings, print order, both branch paths, full Boolean truth tables/nesting and all four loop forms.
- Check zero/multiple arguments, numeric/procedure contexts, nested calls, calls in return/condition/operand positions, repeated labeled functions and captured ancestor writes.
- Tokenize executable target code to detect duplicate/dangling labels, undeclared storage, raw # identifiers, multiple mains, runtime SPL calls and prohibited ELSE/Boolean composition. Ignore strings/comments and the non-executable code mine.
- Use exact integer comparisons and suitable documented float tolerances; verify div(5,2)=2.5 and mod(5,2)=1, not merely a successful target exit.
- Set explicit compile/runtime timeouts and bounded test programs. Infinite loops caused by incorrect lowering must create actionable failures.
- Retain frontend regression coverage while final success cases are semantic-valid. Publish a concise coverage/failure summary for the shared tracker.

#### Required tests and evidence

- The ten planning anchors E01-E10 are represented with correct semantic success/error expectations; parser validity was checked during planning, not P2 execution.
- A deliberately broken false fall-through, reused label, reversed parameter copy and stale capture is detected by at least one focused behavioral test.
- A structurally legal but behaviorally wrong target fails, and a string containing words such as else/not does not trigger a structural false positive.
- A failing target compiler or timeout saves sufficient artifacts to reproduce the case with one documented command.
- Supply the same curated/seeded corpus to [P2-15 / #35](https://github.com/RudolphLamp/coco/issues/35), where native package reruns and source/package agreement are recorded. The source-based harness does not wait for that downstream package to be built.

#### Acceptance criteria

- Every required backend construct has actual target-compile-and-execute evidence.
- The requirement matrix identifies gaps/failures honestly; no unchecked or expected-to-fail required case is hidden in a pass summary.
- Reports are reproducible and usable by the native release gate without source inspection by tutors.

## Focused verification commands

These are the required suite names for the owned implementations. If a
suite is still absent on your base, implement it with that issue or choose
the correct dependency branch; absence is not a passing check. Do not run
a nonexistent module and report it as a product regression on P1 main.

```sh
# Add these suites under their matching owned issues:
PYTHONPATH=src python3 -m unittest tests.unit.test_codegen_ir tests.unit.test_target_writer tests.integration.test_target_skeleton -v
PYTHONPATH=src python3 -m unittest tests.unit.test_codegen_terms tests.integration.test_codegen_arithmetic -v
PYTHONPATH=src python3 -m unittest tests.unit.test_boolean_codegen tests.integration.test_codegen_control_flow -v
PYTHONPATH=src python3 -m unittest tests.integration.test_executable_semantics -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests tools
PYTHONPATH=src python3 tools/black_box_test.py
git diff --check
```

For target generation/inlining, also run real target compilation/execution
with explicit timeouts and independent expected output. Record actual OS,
Python and target-toolchain versions. A stub/model pass is not a final
semantic/target/native pass. Preserve logs and seeds for failures.

## Definition of done and handoff

- Implementation and meaningful focused tests cover the owned checklist,
  with real dependency integration before claiming completion.
- The branch is pushed and a focused PR links the issue, its actual base/
  parent PR and the named reviewer. Do not merge pending work as reviewed.
- Include changed paths, public API, commit, exact commands/results,
  a concrete valid/invalid example, provisional decisions, unrun checks
  and remaining human gates using the shared handoff template.
- Demonstrate the public boundary to the consuming member and record the
  actual outcome. Self-written consumer fixtures do not claim their review.
- Keep the issue/tracker evidence accurate; no completion claim while a
  required dependency, review, test or applicable release gate is missing.
- Send downstream consumers the interface/example and reproducible corpus;
  coordination alone does not substitute for your technical implementation.
