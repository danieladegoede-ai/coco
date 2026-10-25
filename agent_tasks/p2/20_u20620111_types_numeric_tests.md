# u20620111 / Kuda / Kuda21: numeric policy, types, semantic generator and adversarial tests

> Release instruction, 25 October: the Speaker finalized D01-D08 without
> tutor consultation and appointed this AI as main technical reviewer. Use
> [the final release contract](../../release/P2_RELEASE_DECISIONS.md). The dated
> allocations/proposals below are historical and add no consultation or
> named-peer technical-review gate. A33 personal signatures/upload remain real
> personal actions.

Updated 18 October 2026. Primary issues: **#24, #25, #32, #33**. This packet contains
the detailed issue requirements locally so your AI can work without this
conversation. Read live issues/PRs for subsequent changes and actual status.
Requirements below are task checklists, not assertions that work is complete.

## Copy this starting prompt to your AI

```text
You are helping Kuda (u20620111, GitHub Kuda21) on Group 2 COS341
2026 P2, targeting 1st Class. Read root AGENTS.md, agent_tasks/p2/00_START_HERE.md,
agent_tasks/p2/20_u20620111_types_numeric_tests.md, the shared interfaces and handoff guide,
then inspect the live repository and my issues: #24, #25, #32, #33.
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

1. Read #22's semantic/tree APIs and review #23's actual bindings. #24 can
   be developed against the foundation branch with parser-produced trees;
   do not wait for the entire backend to test the global numeric rules.
2. Start #32's bounded source/model generator and independent oracle in its
   owned tool files. Keep the P1 syntax generator unchanged. Formal #21 review
   remains a dependency; independently useful fixtures do not remove that gate.
3. Implement #25 on real ResolvedProgram results once #23 is available on your
   explicit base. Seed all signatures before checking calls, check every body,
   and produce the actual CheckedProgram boundary consumed by both backends.
4. Agree a small immutable numeric-scan result and error precedence with the
   driver/backend owners. Record selected mode and all D04/D05 assumptions.
5. Build #33's positive/one-fault-negative manifest early; connect it to real
   stage APIs and then #31's full CLI. Supply source-based runnable cases to
   #35 without waiting for a native binary, avoiding a circular release gate.

## Ownership and coordination boundaries

- Own numeric_policy.py, type_analysis.py and your named generator/oracle/
  mutation tests/tools/fixtures. Do not reimplement name resolution, codegen
  IR or the final driver. Consult source/path ownership in each issue below.
- Consume original node IDs, ResolvedProgram bindings and body scopes. Produce
  new typed snapshots with dataclasses.replace; do not mutate shared symbols.
- Leave grammar-impossible type forms as defensive model tests rather than
  claiming those are source-language negative cases. Every semantic-negative
  source must pass the real lexer/parser first.
- Generator initialization, bounded loops, nonzero divisors and safe sizes
  keep runtime tests meaningful; they are not new SPL rejection rules.
- The oracle uses independent evaluation, never emitted target or backend IR
  as its expected answer. Test it against hand-computed anchors.
- Review #23 names, #27 arithmetic, #28 truth-table cross-check and #34 target
  acceptance; help review foundation annotations in #22.

## Concrete anchors your implementation must distinguish

- `#x : : #x = add ( mod ( 5 2 ) div ( 4 2 ) ) ; ` rejects with exactly
  `A float-integer-conflict might perhaps be possible`.
- `#x : : #x = mod ( 5 2.1 ) ; ` rejects decimal-with-mod. Put conflicts
  in different uncalled functions and final returns too. A dot/operator word
  in STRING/comment text alone is not a numeric fact.
- `: num #f ( ) { : : return ( 1 ) } : #f ( ) ; ` is syntax-valid but
  type-invalid: INSTR -> CALL requires procedure.
- `: void #f ( ) { : : return } : print ( #f ( ) ) ; ` rejects a procedure
  used as numeric. Numeric calls in assignments/prints/conditions/returns pass.
- Check every nullable production and every type-rule family. The root is OK,
  all semantic attributes are known and every bound name matches its symbol.
- Numeric anchors eventually execute div(5,2)=2.5 and mod(5,2)=1. Full-pipeline
  behavior must match oracle events, not just string snapshots or exit status.

## Detailed owned issues

The requirements below are copied from the live assigned issue snapshot.
The linked issue remains the live progress/review record. Proposed paths
and interfaces must be reconciled with the actual branch; do not invent
missing implementations or cross-owner approvals. Retain real dependency
gates even when independent work can begin.

### [#24: [P2-05][u20620111] Implement whole-program numeric restrictions and backend int/float mode](https://github.com/RudolphLamp/coco/issues/24)

**Reviewer:** `CheriseHeyl`. Review does not transfer implementation ownership.

#### Outcome

Detect the two explicit numeric conflicts anywhere in the entire syntax tree and give the backend a consistent whole-program numeric mode. This helper must distinguish actual operators/NUM tokens from matching text inside strings/comments.

#### Dependencies and independent start

Complete the interfaces/results in [P2-02 / #22](https://github.com/RudolphLamp/coco/issues/22) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/numeric_policy.py`
- `tests/unit/test_numeric_policy.py`
- `tests/fixtures/semantics/numeric/`
- `agent_tasks/p2/00_p2_decisions.md (numeric policy section, coordinate with owner)`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Scan the entire tree, including unused/nested function bodies and return terms, for mod, div and decimal NUM leaves.
- If both mod and div occur, reject with the exact required message: `A float-integer-conflict might perhaps be possible`.
- If any mod occurs, reject any NUM token containing a decimal point anywhere else in the program.
- Recognize operators by grammar/token role, not raw substring; strings containing mod/div or punctuation do not create conflicts.
- Propose and isolate mode selection: int for mod; float for div or a decimal literal; otherwise int. Confirm with the tutor and record any change centrally.
- Do not require integer-looking literals under div to contain decimal points: only the sheet's explicit global errors cause rejection.
- Return a small immutable result describing selected mode and scan facts, with deterministic error precedence when both global conflicts exist.
- Coordinate numeric storage and literal rendering with the target IR/arithmetic owner; all user variables, argument captures, return locations and temporaries must follow the same selected mode.

#### Required tests and evidence

- Neither operator; only mod; only div; decimal without either operator; negative valid decimal; operators spread across different functions.
- `#x : : #x = add ( mod ( 5 2 ) div ( 4 2 ) ) ; ` produces the exact conflict message.
- `#x : : #x = mod ( 5 2.1 ) ; ` fails decimal-with-mod; a dot inside an allowed string alone does not.
- A div inside an uncalled function conflicts with mod in main, and a decimal inside an uncalled function conflicts with mod elsewhere.
- Integration anchor: `#x : : #x = div ( 5 2 ) ; print ( #x ) ; ` eventually executes with numeric output 2.5; mod(5,2) gives 1.
- Repeat/empty scans reset all facts and never leak a previous program's mode.

#### Acceptance criteria

- Both explicit global restrictions have exact regression evidence over the whole tree.
- Mode selection is documented as confirmed/provisional and passed once to all generation stages.
- No accidental integer division or floating-point modulo is introduced by the backend storage policy.

### [#25: [P2-04][u20620111] Implement Part 2b production-based type analysis and call-context checking](https://github.com/RudolphLamp/coco/issues/25)

**Reviewer:** `RudolphLamp`. Review does not transfer implementation ownership.

#### Outcome

Produce a completely checked program from resolved symbols and the supplied grammar-based semantic rules. A statically invalid program must fail before code generation, while a compliant tree must not receive invented type errors.

#### Dependencies and independent start

Complete the interfaces/results in [P2-03 / #23](https://github.com/RudolphLamp/coco/issues/23), [P2-05 / #24](https://github.com/RudolphLamp/coco/issues/24) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `src/spl_frontend/type_analysis.py`
- `tests/unit/test_type_analysis.py`
- `tests/fixtures/semantics/types/`
- `agent_tasks/p2/part_2b_types.md`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Initialize semantic node attributes as unknown and seed declaration signatures before traversing call bodies: variables/parameters numeric, void functions procedure, num functions numeric.
- Implement nullable V_DECL/F_DECL/ALGO/INPUT -> ok and propagate success through F_TYPE, INSTR, ALGO, P and SPL_PROG.
- For num functions, check the return TERM in the function body environment and require numeric. Validate all bodies even when uncalled.
- Require numeric INPUT terms and derive CALL type from its resolved function symbol. Apply the agreed arity policy once recorded, without silently inventing it.
- Require procedure for INSTR -> CALL and numeric for TERM -> CALL. Reject discarding a num result as a standalone call and using a void result in a numeric expression.
- Require numeric assignment target/value, numeric variable/NUM terms, two numeric operands for add/sub/mul/div/mod and one for neg.
- Require numeric eq/larger/lesser operands -> boolean; boolean not/and/or operands -> boolean; boolean branch/loop conditions and ok bodies/COND.
- Accept string output and comments; numeric output requires a numeric TERM. Keep strings out of arithmetic.
- Integrate the whole-program numeric scan from [P2-05 / #24](https://github.com/RudolphLamp/coco/issues/24); expose one checked numeric mode to the backend and stop generation on any confirmed error.
- Return type_by_node plus checked symbols; define semantic type requirements for punctuation/nonsemantic leaves explicitly rather than falsely requiring every punctuation leaf to be numeric/ok.

#### Required tests and evidence

- Cover every rule family with valid trees and reachable invalid SPL fixtures; use deliberately malformed model fixtures only for defensive invariant tests, not purported source-language cases.
- ` : num #f ( ) { : : return ( 1 ) } : #f ( ) ; ` is parser-valid but must produce a type error.
- ` : void #f ( ) { : : return } : print ( #f ( ) ) ; ` must reject a procedure result in a numeric context.
- Numeric calls in assignment, output, arithmetic operands, comparison operands and return terms succeed.
- Uncalled invalid body, nested function, empty algorithm/declarations and repeated independent compilations are checked correctly.
- Diagnostics identify the real source occurrence and expected/actual semantic kind; expected failures have no traceback.

#### Acceptance criteria

- T01-T10 are accounted for, the root program is semantically ok on success and no required type remains unresolved.
- The code generator can accept only a successfully checked program through its documented interface.
- All explicit numeric restrictions are enforced without additional unsupported language restrictions.

### [#32: [P2-12][u20620111] Build a seeded semantic-valid SPL generator and independent runtime oracle](https://github.com/RudolphLamp/coco/issues/32)

**Reviewer:** `CheriseHeyl`. Review does not transfer implementation ownership.

#### Outcome

Generate programs that are syntactically, scope-wise and type-wise valid, terminate, and have independently known observable results. The P1 grammar generator deliberately ignores semantics and cannot serve as the success corpus for the final compiler.

#### Dependencies and independent start

Complete the interfaces/results in [P2-01 / #21](https://github.com/RudolphLamp/coco/issues/21) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `tools/generate_semantic_spl.py`
- `tools/reference_spl_evaluator.py`
- `tests/generated/test_semantic_generator.py`
- `tests/unit/test_reference_spl_evaluator.py`
- `tests/fixtures/semantic_oracle/`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Use deterministic seeds and explicit bounds on source size, expression depth, function depth, loop iterations and runtime steps.
- Track declared variable environments and direct-child callable functions while generating; permit legal ancestor access/shadowing without sideways or recursive calls.
- Generate matching procedure/numeric call contexts and signatures, numeric arguments/returns and no invalid global mod/div or decimal-with-mod combinations.
- Initialize every variable before a generated runtime read and avoid zero divisors, overflow-sensitive boundary values and unbounded loops. These are test-generator constraints, not extra SPL language errors.
- Create guaranteed coverage cases as well as random selections: arithmetic, Boolean compositions, all loop forms, nested/repeated calls, return terms and captured writes.
- Implement an independent small evaluator over a neutral fixture/source model, not the code generator's IR or emitted target. It is a test-only oracle, not the submitted target backend.
- Model numeric mode and sequential Boolean/evaluation semantics according to recorded decisions; use robust float comparison while preserving exact string output events.
- Record seed, input, feature/requirement coverage and expected output/termination; make a failing input reproducible as a standalone fixture.
- Document limits and avoid claiming seed count is proof of complete language correctness. Preserve the P1 syntax generator as its own frontend tool.

#### Required tests and evidence

- Every seed within a selected reproducible smoke range terminates generation and respects configured size/depth limits.
- Hand-computed oracle anchors cover arithmetic precedence via nested terms, if paths, four loops, nested functions and captured parent updates.
- Generated examples pass the frontend and later the real name/type passes; oracle expected results are independently checked against handwritten fixtures.
- The same seed gives identical source and expected events; different generation runs do not retain old scopes/state.
- Generator feature counters prove guaranteed coverage cases were emitted rather than hoping random selection exercised a production.
- Runtime/step limits fail clearly and save the seed/input instead of hanging or silently truncating expected output.

#### Acceptance criteria

- The integration/test owners can request bounded valid programs and known outcomes through a documented CLI/API.
- The oracle has independent hand-verified tests and does not mirror the target lowering implementation.
- Seeds and feature coverage are captured in failure reports usable by each implementation owner.

### [#33: [P2-13][u20620111] Create adversarial name/type regressions and one-fault semantic mutations](https://github.com/RudolphLamp/coco/issues/33)

**Reviewer:** `RudolphLamp`. Review does not transfer implementation ownership.

#### Outcome

Prove the compiler rejects statically invalid names/types for the correct reason and still accepts confirmed legal boundary cases. Each semantic negative case must be parser-valid and isolate one intended naming/type defect.

#### Dependencies and independent start

Complete the interfaces/results in [P2-03 / #23](https://github.com/RudolphLamp/coco/issues/23), [P2-04 / #25](https://github.com/RudolphLamp/coco/issues/25), [P2-05 / #24](https://github.com/RudolphLamp/coco/issues/24), [P2-11 / #31](https://github.com/RudolphLamp/coco/issues/31) before claiming this issue complete. You may begin focused tests and fixtures against those agreed interfaces while implementation proceeds.

#### Proposed owned files

- `tools/mutate_semantic_spl.py`
- `tests/integration/test_semantic_acceptance.py`
- `tests/fixtures/semantics/adversarial/`
- `tests/fixtures/semantics/cases.json`

These are proposed P2 paths. Coordinate changes to shared P1 modules with their recorded owners; keep the existing lexer, grammar, node IDs and XML contract stable. A necessary shared-contract change must update the decision/contract document and its integration tests together.

#### Implementation checklist

- Build a case manifest with ID, requirement IDs, source, expected phase/code/result, relevant location range and explanation.
- Start each negative fixture from a known-valid semantic program; keep its positive partner and make one deliberate change.
- Cover undeclared variables, sideways/cousin lookup, nearest ancestor selection, duplicates, parameter masking and no function overloading.
- Cover illegal self/sibling/ancestor/deep-descendant calls and legal direct-child calls with similar names so permissive lookup cannot pass unnoticed.
- Cover procedure-in-numeric context, num-in-instruction context, nested call returns and errors in uncalled bodies.
- Place mod/div and decimal/mod conflicts in different functions, unused bodies and returns; distinguish numeric literal dots from string text.
- Assert exact required mod/div conflict message and meaningful actual input paths/locations for other errors.
- Add positive cases for empty constructs, bare # user name, legal same-spelling symbols in distinct scopes, deep ancestor access and legal decimal/div inputs.
- Keep tutor-dependent arity/namespace/numeric-mode cases tagged as confirmed or provisional; do not encode an unresolved assumption as official truth.
- Run each case through stage APIs and the final CLI; require no stale target output on rejection. Preserve published P1 syntax-only acceptance fixtures separately.

#### Required tests and evidence

- Check every semantic-negative source parses before asserting a name/type error; a lexical/syntax failure is a fixture bug.
- Mutations are deterministic and record seed plus the exact change; positive counterparts pass names/types.
- Same-level cousins with distinct declarations test scope identity rather than numeric depth alone.
- Multiple-error fixtures, if included, assert only the documented deterministic first-error policy; focused cases remain single-fault.
- Cross-check diagnostic paths for optional explicit filenames and spaces; do not regress P1 issue #18.
- Deliver the runnable matrix to [P2-15 / #35](https://github.com/RudolphLamp/coco/issues/35); native packaged execution is recorded there. This fixture task can close after its source-based suite and manifest pass, avoiding a circular release dependency.

#### Acceptance criteria

- Every confirmed naming/type rejection rule and key legal boundary has an independently reviewed fixture.
- Failures occur in the intended phase with appropriate diagnostics and safe output state.
- The manifest links requirements to concrete passing evidence, not only checklist claims.

## Focused verification commands

These are the required suite names for the owned implementations. If a
suite is still absent on your base, implement it with that issue or choose
the correct dependency branch; absence is not a passing check. Do not run
a nonexistent module and report it as a product regression on P1 main.

```sh
# These suites must be added in the corresponding owned issues:
PYTHONPATH=src python3 -m unittest tests.unit.test_numeric_policy tests.unit.test_type_analysis -v
PYTHONPATH=src python3 -m unittest tests.generated.test_semantic_generator tests.unit.test_reference_spl_evaluator -v
PYTHONPATH=src python3 -m unittest tests.integration.test_semantic_acceptance -v
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
