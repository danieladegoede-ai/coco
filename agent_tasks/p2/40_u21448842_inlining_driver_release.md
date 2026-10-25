# u21448842 / Michele / michey-n: function templates, inlining, compiler driver and native release

> Release instruction, 25 October: the Speaker finalized D01-D08 without
> tutor consultation and appointed this AI as main technical reviewer. Use
> [the final release contract](../../release/P2_RELEASE_DECISIONS.md). The dated
> allocations/proposals below are historical and add no consultation or
> named-peer technical-review gate. A33 personal signatures/upload remain real
> personal actions.

Updated 18 October 2026. Primary issues: **#29, #30, #31, #35**. This packet contains
the detailed issue requirements locally so your AI can work without this
conversation. Read live issues/PRs for subsequent changes and actual status.
Requirements below are task checklists, not assertions that work is complete.

## Copy this starting prompt to your AI

```text
You are helping Michele (u21448842, GitHub michey-n) on Group 2 COS341
2026 P2, targeting 1st Class. Read root AGENTS.md, agent_tasks/p2/00_START_HERE.md,
agent_tasks/p2/40_u21448842_inlining_driver_release.md, the shared interfaces and handoff guide,
then inspect the live repository and my issues: #29, #30, #31, #35.
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

1. Read the real #22/#23 model and call hierarchy, then coordinate #26's
   structural IR with Cherise. #29's template/environment tests can begin
   against explicit resolved-model fixtures while IR integration is pending.
2. Implement declaration identity versus per-call storage mapping before #30.
   Test a child capturing the current parent's local and a same-spelling
   unrelated symbol. Never rediscover scope through raw target identifiers.
3. Implement #30 actual capture, formal copy, fresh label/storage remapping,
   return continuations and bottom-up nested expansion. Isolate D02/D04 and
   use a nonzero argument to expose reversed copy direction immediately.
4. Scaffold #31's coordinator/output lifecycle with explicit test doubles if
   dependencies are pending; replace them with the real names/types/generator
   before claiming full integration. Keep a deliberate frontend-only API for
   existing syntax tests and make the final assessment command run all passes.
5. Start #35's reproducible build scaffold early. Diagnose the real Actions
   startup issue without pretending hosted jobs passed; native acceptance
   waits on #31/#33/#34 and the exact final binary/corpus. Provide Rudolph
   hashes, toolchain/platform/version, commit and launch evidence.

## Ownership and coordination boundaries

- Own function_templates.py, expansion_environment.py, inlining.py, final
  compiler/CLI/diagnostic coordination and native packaging files named below.
- Preserve existing P1 source/lexer/parser/tree contracts. New phases/statuses
  and any tree.xml lifecycle change are coordinated and regression-tested.
- Use Cherise's IR/term/Boolean interfaces and Kuda's checked mode/results.
  Do not duplicate arithmetic generation, infer names from strings or build
  a second semantic pass inside the driver.
- Code-mine templates are reusable non-executable definitions. Expand every
  required SPL call structurally; no runtime SPL functions or stack substitute.
- Detect source/output aliases before cleanup. Clear failed-run target state
  safely and publish final source atomically only after required passes succeed.
- Build Windows artifacts on Windows for the confirmed architecture, not by
  renaming a Mac/Linux file. A supplementary Linux executable has no extension.
  Do not claim dependency-free target compilation merely because the compiler
  binary itself bundles Python.
- Review #22 source/XML/model linkage, #26 IR, #28 control flow and #21's
  technical baseline. Feature review does not happen automatically in tests.

## Concrete anchors your implementation must distinguish

- Capture actual TERM results before populating cloned formals; earlier
  captures must survive later argument side effects under the recorded order.
  Test zero/one/multiple actuals and nested operands as single arguments.
- `#x : num #f ( #a ) { #v : void #g ( ) { : : #v = add ( #v 1 ) ; return }
  : #v = #a ; #g ( ) ; return ( #v ) } : #x = #f ( 4 ) ; print ( #x ) ; `
  must produce 5. Repeat with a new actual to verify the child updates the
  new parent instance rather than the previous call's storage.
- A loop-containing function called with 2 then 3 yields those two numeric
  output events in order, with unique labels/storage in both expansions.
- Numeric calls work in assignment/print/arithmetic/comparison/actual/return
  positions. A procedure call gets no fabricated numeric return location.
- Test default and explicit paths, spaces, input aliasing XML/target, denied
  writes, and valid -> error in each phase -> valid sequences. Expected errors
  show the actual source path and no traceback; stale targets never survive.
- Run source and actual packaged compilers on identical case IDs/seeds, then
  compile/execute their targets. Hash the tested binary and deliver that exact
  file to Rudolph; a source-only pass cannot certify a native artifact.

## Detailed owned issues

The requirements below are copied from the live assigned issue snapshot.
The linked issue remains the live progress/review record. Proposed paths
and interfaces must be reconciled with the actual branch; do not invent
missing implementations or cross-owner approvals. Retain real dependency
gates even when independent work can begin.

### [#29: [P2-09][u21448842] Build function code-mine templates and lexical expansion environments](https://github.com/RudolphLamp/coco/issues/29)

**Reviewer:** `RudolphLamp`. Review does not transfer implementation ownership.

#### Outcome

Represent every resolved function as a reusable non-executable template and preserve the lexical environment needed for later inline expansion. Functions must not become ordinary runtime target functions or accidentally emit nested main definitions.

#### Dependencies and independent start

Complete the interfaces/results in [P2-02 / #22](https://github.com/RudolphLamp/coco/issues/22), [P2-03 / #23](https://github.com/RudolphLamp/coco/issues/23), [P2-06 / #26](https://github.com/RudolphLamp/coco/issues/26) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/function_templates.py`
- `src/spl_frontend/expansion_environment.py`
- `tests/unit/test_function_templates.py`
- `tests/unit/test_expansion_environment.py`
- `tests/fixtures/codegen/function_templates/`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Define FunctionTemplate using resolved function symbol ID, ordered formal symbols, owned locals, return kind/TERM, body IR, label identities and referenced ancestor symbols.
- Map each function to its body P and children; create templates from the resolved/checked tree rather than re-parsing source text.
- Keep declaration-time symbol identity distinct from per-call storage identity. Define ExpansionEnvironment mappings for current locals, formals, returns and ancestor captures.
- Build the child-before-parent template preparation order. A nested child is expanded into the parent template before that expanded parent is placed in executable main.
- Ensure lookup of a captured variable follows the already-resolved declaration symbol and current parent environment, never raw spelling or a sibling's storage.
- Specify structural template cloning/remapping with the target IR owner; strings/comments must not be renamed by textual substitution.
- Render a safe non-executable code-mine view through the target writer, including function identity, parameters, body and numeric return location information.
- Keep code-mine comment delimiters valid even when template bodies contain generated nop/comment annotations; no template statements execute merely because declared.
- Detect malformed/cyclic resolved function structures defensively and report a generation invariant error, without adding recursion support.

#### Required tests and evidence

- Void/num functions with zero, one and multiple parameters; nested functions with their own declarations and a return TERM.
- Parent/child/grandchild template creation uses dependency order and retains correct symbol references.
- A child reading/updating a parent local captures that exact symbol; a same-spelling variable in a different scope remains distinct.
- Uncalled functions produce no stdout/state changes; an emitted code mine stays entirely non-executable.
- Template render with nested instruction comments compiles as part of the final target skeleton.
- Expanding/cloning a template does not mutate its reusable definition or affect a later call.

#### Acceptance criteria

- The inliner can instantiate templates using the documented environment without rediscovering lexical scope.
- Function bodies remain non-executable until expanded and the rendered program has exactly one main.
- Nested capture identity and safe reusable templates have focused tests, not only end-to-end snapshots.

### [#30: [P2-10][u21448842] Implement function inlining, argument capture, returns and fresh per-call labels/storage](https://github.com/RudolphLamp/coco/issues/30)

**Reviewer:** `CheriseHeyl`. Review does not transfer implementation ownership.

#### Outcome

Make void and numeric SPL calls execute correctly by structural expansion of the function code mine. This includes nested calls, return continuations, repeated calls containing jumps and writes through captured ancestor variables.

#### Dependencies and independent start

Complete the interfaces/results in [P2-04 / #25](https://github.com/RudolphLamp/coco/issues/25), [P2-07 / #27](https://github.com/RudolphLamp/coco/issues/27), [P2-08 / #28](https://github.com/RudolphLamp/coco/issues/28), [P2-09 / #29](https://github.com/RudolphLamp/coco/issues/29) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/inlining.py`
- `tests/unit/test_inlining.py`
- `tests/integration/test_codegen_calls.py`
- `tests/fixtures/codegen/calls/`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Walk the recursive INPUT chain and preserve ordered TERM arguments; nested operands inside one TERM are not extra inputs.
- Evaluate all actual terms into fresh capture temporaries before assigning the cloned formals. Use the recorded arity/evaluation-order policy; report mismatches according to that decision.
- Populate formal storage from captured actual values. The sheet's pN=aN example appears reversed; document the intended data flow and obtain/record the tutor answer from [P2-01 / #21](https://github.com/RudolphLamp/coco/issues/21).
- Instantiate fresh per-call formal/local/return storage and labels; remap every reference, definition and goto target together using structural IDs.
- Inline void calls in instruction position with no fabricated return value; inline num calls by evaluating the body return TERM and copying the result into the caller-provided continuation location.
- Support numeric calls inside assignment, print, arithmetic/comparison operands, other call arguments and a function's return TERM.
- Expand child/grandchild calls within the current parent environment before final main placement, maintaining references to the correct instantiated ancestor locals.
- Preserve root shared variables; captured writes must update the current ancestor instance rather than a fresh detached copy.
- Repeat expansion without mutating reusable templates. Validate no duplicated labels, unresolved symbols or runtime SPL function calls remain in executable target code.
- Use bounded expansion/invariant checks for malformed inputs; never substitute runtime recursion or stack-based functions for the required inlining technique.

#### Required tests and evidence

- Zero, one and several arguments; numeric actuals distinguish a reversed copy using a non-zero value.
- Argument expressions with outer-state effects prove earlier captured values survive later argument evaluation under the agreed order.
- The same loop-containing numeric function called with inputs 2 and 3 prints output events 2 then 3; labels and storage differ across expansions.
- Parent -> child -> grandchild expansion and calls in return terms execute correctly.
- `#x : num #f ( #a ) { #v : void #g ( ) { : : #v = add ( #v 1 ) ; return } : #v = #a ; #g ( ) ; return ( #v ) } : #x = #f ( 4 ) ; print ( #x ) ; ` prints 5.
- Repeat the parent call with a different argument and prove its child updates the new parent instance, not the first instance.
- Same-spelling different symbols, longer identifier spellings and string/comment text are not accidentally rewritten.

#### Acceptance criteria

- Every F03-F08 requirement has compile-and-run evidence using real generated target code.
- All call sites use fresh labels and appropriate storage with correct captures/returns.
- There are no executable runtime SPL function calls, duplicate labels, nested mains or code-mine leaks.

### [#31: [P2-11][u21448842] Integrate the full compiler CLI, semantic diagnostics and safe target-output lifecycle](https://github.com/RudolphLamp/coco/issues/31)

**Reviewer:** `RudolphLamp`. Review does not transfer implementation ownership.

#### Outcome

Make the public command run SPL input through parser, names, types, code generation and inlining to fresh target source. Keep frontend-only regression coverage deliberate, and ensure failed runs cannot leave old target output looking successful.

#### Dependencies and independent start

Complete the interfaces/results in [P2-02 / #22](https://github.com/RudolphLamp/coco/issues/22), [P2-04 / #25](https://github.com/RudolphLamp/coco/issues/25), [P2-05 / #24](https://github.com/RudolphLamp/coco/issues/24), [P2-07 / #27](https://github.com/RudolphLamp/coco/issues/27), [P2-08 / #28](https://github.com/RudolphLamp/coco/issues/28), [P2-10 / #30](https://github.com/RudolphLamp/coco/issues/30) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/compiler.py`
- `src/spl_frontend/cli.py`
- `src/spl_frontend/cli_contract.py`
- `src/spl_frontend/diagnostics.py`
- `src/spl_frontend/__main__.py`
- `tests/test_cli.py`
- `tests/integration/test_full_compiler.py`
- `tests/integration/test_output_lifecycle.py`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Preserve default SPL.txt input and optional explicit path unless a confirmed assessment command requires a change. Pass actual source paths through every diagnostic phase.
- Run parse/tree validation -> resolved names/renamed view -> whole-program numeric/type checks -> checked-code generation/templates/inlining -> validated target serialization.
- Expose a documented frontend-only entry point/stage for parser regression tests; the final default assessment command must run the full compiler, not silently stop at tree.xml.
- Add name/type/generation diagnostic phases and stable non-zero failure statuses without changing P1 statuses unnecessarily. Library modules raise structured errors; only CLI renders them.
- Implement the agreed target filename/location and atomic publication. Clear/invalidate stale target output before an attempt and never publish a partial target on lexical, syntax, name, type, generation or write failure.
- Preserve source input safely: detect identical/aliased input and output locations before deletion/replacement; account for tree.xml and target paths.
- Keep tree.xml behavior consistent with the documented stage/output policy. Do not silently reverse the existing stale-XML rule; any necessary change is explicit, coordinated and regression-tested.
- Support the XML-to-semantic path from [P2-02 / #22](https://github.com/RudolphLamp/coco/issues/22), or document the agreed equivalent pipeline entry; round-trip and in-memory semantics must agree.
- Do not require a target compiler merely to generate source unless the team/tutor contract explicitly chooses automatic compile/run. If automatic invocation is implemented, detect missing tools and document the dependency.
- Migrate frontend-specific CLI fixtures to the frontend stage without deleting assertions; final full-pipeline success fixtures must be scope/type-correct.

#### Required tests and evidence

- Default and explicit paths, paths with spaces, missing/unreadable/non-ASCII input and usage errors.
- Valid -> lexical/syntax/name/type/generation failure -> valid sequences: correct exit codes, helpful stderr, no stale/partial successful-looking target.
- Input equals XML/target output, path aliases, denied output writes and repeated independent runs never delete input or mix state.
- The full CLI compiles a declared-variable arithmetic case and a nested/repeated-call case, with emitted target subsequently compiled and executed.
- XML round-trip semantics and in-memory semantics produce equivalent checked/generated behavior.
- Expected failures contain no Python traceback and report the actual input path; preserve coverage related to existing issue #18.

#### Acceptance criteria

- The exact public command intended for tutors reaches correct target source on valid input and reliably rejects invalid input.
- Output lifecycle and source preservation are verified end to end, not only within the XML writer.
- Frontend regression and final semantic/code-generation tests coexist with clearly distinct expectations.

### [#35: [P2-15][u21448842] Build native P2 executables and test the exact packaged artifacts in CI](https://github.com/RudolphLamp/coco/issues/35)

**Reviewer:** `CheriseHeyl`. Review does not transfer implementation ownership.

#### Outcome

Produce the assessment-ready native compiler from one recorded commit, then run the same semantic and executable-target corpus against that artifact. Begin the build scaffold early; final acceptance waits for the full integration/verification suites.

#### Dependencies and independent start

Complete the interfaces/results in [P2-11 / #31](https://github.com/RudolphLamp/coco/issues/31), [P2-13 / #33](https://github.com/RudolphLamp/coco/issues/33), [P2-14 / #34](https://github.com/RudolphLamp/coco/issues/34) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `.github/workflows/test-and-build-spl.yml (new/reconciled for this team repo)`
- `ci/test_packaged_p2.py`
- `tools/black_box_test.py`
- `tests/test_black_box.py`
- `release/P2_BUILD.md`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Confirm tutor Windows OS/CPU and executable command. Use the already successful .exe packaging route; the announcement lists .exe or .jar, so do not ship only a macOS/Linux executable.
- Build on Windows for the Windows artifact; build on Linux only if a supplementary Linux artifact is agreed. A Linux filename is group-2 with no invented extension.
- Pin Python/packaging versions, record source commit and reproducible build commands, and keep generated binaries out of the source branch.
- Run source/focused tests and compileall before packaging, then exercise the resulting executable from fresh directories with no checkout or Python runtime dependency.
- Run names/types rejection matrix and valid full-program behavioral corpus through the packaged compiler, then compile and run its emitted target with the confirmed native toolchain.
- Test default and explicit SPL.txt, paths with spaces, missing/invalid input, valid-invalid-valid lifecycle, repeated runs and actual diagnostic paths.
- Distinguish the dependency-free compiler package from any target compiler needed to build the generated source. Document rather than assume the tutor has an undeclared tool.
- Store artifact hashes and build/test evidence; upload CI artifacts only after their tests pass. Ensure final package uses those tested files, not an earlier local build.
- Compare source and packaged behavior on the same fixture IDs/seeds and investigate differences before release.
- Provide a release manifest of filenames, sizes, hashes, supported platform and source commit for [P2-16 / #36](https://github.com/RudolphLamp/coco/issues/36).

#### Required tests and evidence

- Windows executable identifies as native Windows x86-64 (or confirmed target) and launches without development files/Python installed.
- At least one semantic rejection and one nested/repeated-call program are exercised from the actual final binary, not a source-only subprocess.
- Full applicable N/T/G/F case manifest passes with no silent skips; emitted target compiles and produces the expected result.
- Missing target toolchain, if invoked by the chosen workflow, produces a documented setup error rather than a traceback or false success.
- The release artifact hash equals the tested artifact hash, with logs identifying platform, versions, commit and corpus.

#### Acceptance criteria

- A clean tutor-compatible machine can run the delivered compiler using exactly the manual's command.
- The final native artifact passes the complete agreed black-box and target execution gates.
- The release owner receives verified binaries plus a reproducible provenance/hash record.

## Focused verification commands

These are the required suite names for the owned implementations. If a
suite is still absent on your base, implement it with that issue or choose
the correct dependency branch; absence is not a passing check. Do not run
a nonexistent module and report it as a product regression on P1 main.

```sh
# Add these suites under their matching owned issues:
PYTHONPATH=src python3 -m unittest tests.unit.test_function_templates tests.unit.test_expansion_environment -v
PYTHONPATH=src python3 -m unittest tests.unit.test_inlining tests.integration.test_codegen_calls -v
PYTHONPATH=src python3 -m unittest tests.test_cli tests.integration.test_full_compiler tests.integration.test_output_lifecycle -v
# #35 must document its actual native build/package corpus commands separately.
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
