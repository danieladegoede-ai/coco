# u20598425 / Rudolph / RudolphLamp: foundation, name analysis and final release

> Release instruction, 25 October: the Speaker finalized D01-D08 without
> tutor consultation and appointed this AI as main technical reviewer. Use
> [the final release contract](../../release/P2_RELEASE_DECISIONS.md). The dated
> allocations/proposals below are historical and add no consultation or
> named-peer technical-review gate. A33 personal signatures/upload remain real
> personal actions.

Updated 18 October 2026. Primary issues: **#21, #22, #23, #36**. This packet contains
the detailed issue requirements locally so your AI can work without this
conversation. Read live issues/PRs for subsequent changes and actual status.
Requirements below are task checklists, not assertions that work is complete.

## Copy this starting prompt to your AI

```text
You are helping Rudolph (u20598425, GitHub RudolphLamp) on Group 2 COS341
2026 P2, targeting 1st Class. Read root AGENTS.md, agent_tasks/p2/00_START_HERE.md,
agent_tasks/p2/10_u20598425_foundation_names_release.md, the shared interfaces and handoff guide,
then inspect the live repository and my issues: #21, #22, #23, #36.
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

1. Inspect PR #37 and #38 before writing code. #21/#22 already exist in
   feat/u20598425-p2-foundation; #23 exists in feat/u20598425-p2-names.
   Main-branch absence is not a reason to implement those passes again.
2. Address actual review findings in the appropriate parent branch, preserving
   the small shared APIs and all tests. The foundation must merge before the
   name layer is retargeted to main. Keep both PRs reviewable after doc changes.
3. Demonstrate the public name interface to an actual teammate and record the
   real outcome. A test fixture alone is not that member demonstration.
4. Coordinate the D01-D08 tutor questions, especially D06 names/return scope.
   Record actual dated answers, not assumptions from the planning document.
5. Draft #36's editable manual/release checklist now. Do not claim final
   filenames, target command, signatures, native pass or upload until supplied
   by the relevant real release evidence. Finalize only after #33/#34/#35.

## Ownership and coordination boundaries

- Own tree/XML/source-link/semantic-model/name-analysis changes. Preserve the
  existing lexer/parser/CLI; coordinate any change with its recorded owner.
- Support Kuda's typed snapshot and Michele's capture environment with symbol
  identities, ordered formals, body scope and actual source spans. Do not
  implement their type/inlining modules or choose target IR classes for Cherise.
- For D06 keep current separate namespaces and body-scope returns visibly
  provisional; a tutor answer changes that isolated policy and focused tests.
- Review queue includes #25 types, #29 templates, #31 driver and #33 semantic
  acceptance; all-member #21/#36 gates need real confirmations.
- Personal signatures/approvals belong to each member; the Speaker coordinates
  them but an AI may not sign for anyone or fabricate an upload receipt.

## Concrete anchors your implementation must distinguish

- `: void #f ( #x ) { #x : : return } : ` must fail own-parameter masking
  even when #f is uncalled. A child may legally shadow an ancestor's variable.
- Inspect the A21 g/j versus h/k cousin case: j sees g's x, k never sees it
  sideways. If a real global x exists, k sees that distinct declaration.
- A main direct child call succeeds; self/sibling/ancestor/deep-descendant
  calls fail. Same-spelling declarations have stable distinct internal names.
- Repeated compilation and original/XML/reordered-record trees retain bindings
  and original XML bytes. XML-only errors show node IDs, not fabricated lines.
- Final #36 evidence is the extracted tested package plus accurate PDF, both
  declarations with eight real signatures, matching hashes and downloaded-copy
  retest. A draft PDF or an unsigned checklist is not final evidence.

## Detailed owned issues

The requirements below are copied from the live assigned issue snapshot.
The linked issue remains the live progress/review record. Proposed paths
and interfaces must be reconciled with the actual branch; do not invent
missing implementations or cross-owner approvals. Retain real dependency
gates even when independent work can begin.

### [#21: [P2-01][u20598425] Establish the P2 baseline, shared contracts and tutor decision record](https://github.com/RudolphLamp/coco/issues/21)

**Reviewer:** All four members; technical cross-check by `michey-n`. Review does not transfer implementation ownership.

#### Outcome

Give everyone one complete, reproducible P1 starting point and a current P2 contract. The Desktop `COCO ass/coco` checkout is an old incomplete docs branch; live repository main is already a complete front end. Do not overwrite main with the old checkout or reconstruct a working parser unnecessarily.

#### Dependencies and independent start

This is the starting task. It has no P2 implementation dependency. Publish the small agreed interfaces early so the other owners can start independently.

#### Proposed owned files

- `AGENTS.md`
- `README.md`
- `agent_tasks/00_team_decisions.md`
- `agent_tasks/01_shared_contracts.md`
- `agent_tasks/p2/README.md`
- `agent_tasks/p2/00_p2_decisions.md`
- `agent_tasks/p2/01_p2_contracts.md`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Record live main commit `0be22dbdf614a31a1936f32fec5aede81959ede8` as observed on 17 October, then check for newer team work before creating a P2 branch.
- Preserve every existing working tree and the submitted P1 ZIP. Update/create a complete checkout under COCO ass safely; do not hard-reset another member's branch.
- Compare the submitted-build support checkout (`1e588a9`) with team main. The inspected compiler/parser/tree source already matches; selectively reconcile release CI/tooling rather than replacing the team history.
- Run the complete baseline suite and six published tutor cases at the frontend stage; record actual counts. The complete local source previously passed 267 tests, but count the chosen baseline rather than assuming every checkout is identical.
- Update the frontend-only scope text in AGENTS/README for the full pipeline. Record the new owner allocation and keep the P1 ownership/approval history as history.
- Freeze minimal Scope, Symbol, ResolvedProgram, CheckedProgram, source-map, target IR, template and expansion-environment contracts with the affected owners. Define separate variable lookup and direct-child function lookup APIs.
- Specify the final CLI input/output contract, frontend-only test entry point, node-ID annotations, target-output publication and diagnostic phase/code ownership.
- Create a dated tutor-question/answer record for: C versus C++ examples/toolchain/output suffix; actual-to-formal copy direction; explicit two-target Boolean lowering; arity/evaluation order; numeric mode; namespaces and return-term scope; required semantic outputs; target platform and ClickUp cutoff.
- Prepare the Speaker's focused Tuesday 20 October consultation list. Mark confirmed/provisional policies separately. The shared roadmap tracks obtaining answers and affected follow-up tests; this baseline task can close once usable provisional contracts are recorded, without waiting until Tuesday.

#### Required tests and evidence

- Verify imports/entry point, 267-test local reference, six tutor frontend outcomes, XML determinism and default/explicit input commands on the chosen baseline.
- Demonstrate that P1 tutor T2/T3 remain parser-accepted fixtures even though the final semantic compiler may reject them.
- Have each downstream owner construct one fake/fixture using the shared interfaces and confirm no circular module dependency is needed.
- List unconfirmed policies explicitly. Do not mark tutor questions answered merely because an implementation was proposed.

#### Acceptance criteria

- All four members can identify and run the same complete source baseline in the intended folder.
- Current contracts and ownership are recorded in one location, with conflicting September planning assumptions resolved.
- Other issues can start against small stable models; remaining tutor questions have an owner and planned resolution date.

### [#22: [P2-02][u20598425] Implement semantic data models, concrete-tree walkers and XML/source linkage](https://github.com/RudolphLamp/coco/issues/22)

**Reviewer:** `michey-n`, with `Kuda21` checking annotations. Review does not transfer implementation ownership.

#### Outcome

Provide one reliable representation of scopes, symbols and node annotations for all later passes, plus a validated path from existing tree.xml into those passes. Preserve the successful P1 concrete syntax tree and original source lexemes.

#### Dependencies and independent start

Complete the interfaces/results in [P2-01 / #21](https://github.com/RudolphLamp/coco/issues/21) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/semantic_model.py`
- `src/spl_frontend/tree_walkers.py`
- `src/spl_frontend/tree_reader.py`
- `src/spl_frontend/source_map.py`
- `tests/unit/test_semantic_model.py`
- `tests/unit/test_tree_reader.py`
- `tests/unit/test_tree_walkers.py`
- `tests/integration/test_semantic_tree_roundtrip.py`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Define deterministic Scope IDs, parent links and owning P-node IDs. Distinguish scope identity from numeric nesting depth.
- Define Symbol IDs/kinds, declaration node ID, original spelling, declaring scope, deterministic internal name, type/signature and ordered parameter IDs. Keep variable and function lookup policies distinct.
- Define side maps: scope_by_node, binding_by_name_node, renamed_name_by_node, type_by_node and source_location_by_node. Later passes use resolved identities, not raw-name replacement.
- Implement iterative walkers for recursive V_DECL, F_DECL, INPUT and ALGO list chains. Correctly identify nullable nodes and do not count nested operands as extra call arguments.
- Load the actual existing XML schema, validate node kinds/IDs/links/root/reachability/ordered children, and reject malformed XML or invalid graphs before semantics.
- Round-trip the in-memory parser tree through XML without changing IDs, contents or child order; confirm both paths produce equivalent semantic inputs.
- Map consumed leaf order to non-EOF source tokens, preserving repeated lexemes at different positions. Check token-count/content alignment; never locate occurrences using a spelling-only search.
- Provide node/span-based diagnostics when only XML is available; do not fabricate original line/column data that XML does not contain.
- Keep allocations per compilation; avoid mutable global state and avoid importing code generation into the shared model.

#### Required tests and evidence

- Root-only/minimal grammar trees, empty list nodes and multi-item recursive lists preserve item order.
- Repeated names at different positions map to different leaf locations, including CR/LF/CRLF source layouts.
- Malformed XML, duplicate IDs, dangling children, asymmetric parents, cycles, wrong root and unreachable nodes are rejected.
- In-memory and XML-round-tripped versions produce byte/equality-stable node structures and equivalent scope/binding inputs.
- Deep list chains do not exceed Python recursion limits merely because the parser represented a list recursively.

#### Acceptance criteria

- Names, types, codegen and inlining can consume the same documented model without reimplementing tree walking.
- P1 tree/XML tests remain valid, and original lexemes/node IDs are preserved.
- Invalid XML/source alignment yields a structured actionable failure instead of silently binding the wrong occurrence.

### [#23: [P2-03][u20598425] Implement Part 2a scope rules, name resolution and consistent renaming](https://github.com/RudolphLamp/coco/issues/23)

**Reviewer:** `Kuda21`. Review does not transfer implementation ownership.

#### Outcome

Resolve every variable/function occurrence to the correct declaration, reject all confirmed naming violations and produce deterministic unique internal names for later passes. SPL function visibility is stricter than ordinary ancestor-based variable visibility.

#### Dependencies and independent start

Complete the interfaces/results in [P2-02 / #22](https://github.com/RudolphLamp/coco/issues/22) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/name_analysis.py`
- `tests/unit/test_name_analysis.py`
- `tests/fixtures/semantics/names/`
- `agent_tasks/p2/part_2a_names.md`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Create a root P scope and one body scope per nested function; branches/loops do not introduce declaration scopes in this grammar.
- Collect declarations before checking uses. Parameters and body locals share the same duplicate-check domain for the owning function.
- Resolve variables in the current scope, then nearest ancestor. Never visit sibling or cousin scopes; different siblings at the same depth remain separate.
- Reject duplicate locals, duplicate parameters and a local masking its own parameter. Permit legal deeper shadowing of an ancestor declaration.
- Resolve calls only against the immediate F_DECL owned by the caller P. Main may call its direct functions; a function may call its declared children. Reject self, sibling, ancestor and deep-descendant calls.
- Reject duplicate functions within the applicable declaration list and overloading. Record any variable/function collision policy as a tutor decision, not an invented rejection.
- Validate direct/indirect recursion constraints and make the resolved call hierarchy available for bottom-up expansion; detect a cycle as a protective invariant.
- Resolve assignments, operands, print terms, conditions, call arguments and the final numeric return TERM using the appropriate body scope. Visit uncalled function bodies too.
- Allocate internal names from declaration identity: same computational entity always gets the same internal name; distinct declarations never share it.
- Return structured name diagnostics containing actual input path/location or node ID, original name, failed rule and a helpful hint. Do not print from library code.

#### Required tests and evidence

- Local/outer/global lookup and closest-declaration shadowing; assert exact declaration and internal-name identities.
- Two sibling functions declare/use the same spelling legally; a third sibling cannot read either sibling's local.
- Duplicate parameters, duplicate locals, parameter/local masking and duplicate functions each fail independently.
- Direct child calls succeed; self, mutual-sibling, ancestor and grandchild-from-main calls fail.
- Functions in nested branches/loops and calls in a return TERM use the containing P environment.
- Minimal concrete fixture: `: void #f ( #x ) { #x : : return } : ` must fail the own-parameter masking rule.
- Repeat compilation and XML round-trip runs: bindings and generated internal names remain deterministic.

#### Acceptance criteria

- Every N01-N10 rule has focused positive/negative evidence, including Announcement 21 sideways lookup.
- A compliant program produces no naming error; an invalid naming program cannot enter type checking/code generation.
- The output binding/renaming map is usable directly by the type checker and inliner.

### [#36: [P2-16][u20598425] Finalize launch manual, both personal declarations and verified 1st Class submission](https://github.com/RudolphLamp/coco/issues/36)

**Reviewer:** All four members: `Kuda21`, `CheriseHeyl`, `michey-n` and `RudolphLamp`. Review does not transfer implementation ownership.

#### Outcome

Submit one agreed, tested 1st Class archive with a clear launch manual and both required personally signed declarations. The Speaker coordinates the upload, but every member must understand and approve the actual final files.

#### Dependencies and independent start

Complete the interfaces/results in [P2-13 / #33](https://github.com/RudolphLamp/coco/issues/33), [P2-14 / #34](https://github.com/RudolphLamp/coco/issues/34), [P2-15 / #35](https://github.com/RudolphLamp/coco/issues/35) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `release/P2_USER_MANUAL_SOURCE.md (or agreed editable source)`
- `release/P2_RELEASE_CHECKLIST.md`
- `release/P2_MANIFEST.json (provenance only; no generated executables in source)`
- `Final group-number PDF/ZIP in ignored release output`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Confirm exact group-number naming and final ClickUp slot/closing timestamp. The notice states Sunday 25 October but no hour; plan early upload on 24 October.
- Document members/category, supported OS/CPU, default and explicit input commands, a valid whitespace-correct SPL.txt example and expected visible output.
- Document tree/semantic/target output files, errors/statuses and exact target compile/run commands using the confirmed dialect/toolchain. Distinguish the compiler executable from the program it generates.
- Include Declaration 1: all members unanimously agree on 1st Class, maximum 6/6 P2 points, including Parts 2a/2b/3a/3b and executable target generation.
- Include Declaration 2: each member is fully aware of the entire final ZIP contents and agrees to submission in this form.
- Collect each member's personal signature separately for both declarations. Planning templates/typed owner assignments are not completed signatures; verify any prescribed signature method.
- Render and inspect every final PDF page after signatures. Ensure commands match actual tested filenames and no Phase 1-only description remains.
- Archive the tested executable and final manual plus only confirmed/documented supplementary files. Exclude caches, scratch inputs, old builds, private course sheets and the planning PDF.
- Check archive integrity and record SHA-256 outside the archive. All four members review the same release; changes after approval require renewed accurate review/approval.
- Speaker uploads only to the 1st Class slot. Do not upload in both categories. Download the uploaded file, compare hashes, retest the extracted executable and preserve the receipt/slot evidence.

#### Required tests and evidence

- From the final extracted ZIP, another member follows only the manual and successfully generates, compiles and runs the example.
- A semantic-invalid example produces the documented failure and no misleading target output.
- PDF has both declarations and eight personal signatures total (four members on each), legible command blocks and correct category.
- Archive manifest, tested binary hashes, uploaded/downloaded archive hashes and extracted filenames agree.
- Individual review checklist: Rudolph u20598425; Kuda u20620111; Cherise u21434019; Michele u21448842 each confirm category, contents and demonstrated launch.

#### Acceptance criteria

- The final archive contains the exact tested build and the fully signed, accurate launch manual.
- All members agree on the same 1st Class release; there is one verified upload in the correct slot before the confirmed cutoff.
- Downloaded-copy checks and submission receipt are retained, and any incomplete release condition is reported honestly.

## Focused verification commands

These are the required suite names for the owned implementations. If a
suite is still absent on your base, implement it with that issue or choose
the correct dependency branch; absence is not a passing check. Do not run
a nonexistent module and report it as a product regression on P1 main.

```sh
# On a branch containing #22/#23:
PYTHONPATH=src python3 -m unittest tests.unit.test_semantic_model tests.unit.test_tree_reader tests.unit.test_tree_walkers tests.unit.test_source_map -v
PYTHONPATH=src python3 -m unittest tests.unit.test_name_analysis tests.integration.test_name_analysis_pipeline -v
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
