# Start here: Group 2 Phase 2 AI instructions

Updated 25 October 2026 at the Speaker's request. These guides supersede the
September frontend-only task allocation. The goal is a **1st Class** COS341
2026 submission: Parts **2a, 2b, 3a and 3b**, including correct executable target
generation, for up to **6/6 P2 points**. P1 earned full marks and stays covered.
The final date is **Sunday 25 October**; use the cutoff displayed in First Class.

## Choose the member, then the issue

| Member / GitHub | Work order | Packet |
| --- | --- | --- |
| Rudolph / u20598425 / RudolphLamp | Review existing #21/#22/#23, then #36 release work | [Rudolph](10_u20598425_foundation_names_release.md) |
| Kuda / u20620111 / Kuda21 | #24 numeric scan and #32 generator can start independently on contracts; #25 types; #33 semantic negatives | [Kuda](20_u20620111_types_numeric_tests.md) |
| Cherise / u21434019 / CheriseHeyl | #26 IR; #27 arithmetic; #28 Booleans/loops; #34 executable verification | [Cherise](30_u21434019_codegen_verification.md) |
| Michele / u21448842 / michey-n | #29 templates; #30 inlining; #31 integration; #35 native release | [Michele](40_u21448842_inlining_driver_release.md) |

Each issue retains its original primary owner. The Speaker has designated
this AI as main technical reviewer for the final release. Reviewing does not
transfer implementation ownership. Work is tied to issue paths, not exclusive
ownership of a whole test directory. Do not create overlapping implementations
or take another member's work because its module has not merged yet.

## What exists, and where

Current release status; inspect the live branch and PR before editing:

| Work | Location | Meaning |
| --- | --- | --- |
| Complete P1 source | `src/spl_frontend` | Assessed frontend retained with regression tests |
| Parts 2a/2b/3a/3b | Integrated source, original issues #21-#34 closed | Names/types, target IR, algorithms, templates, inlining and full driver are implemented |
| Source acceptance | `tests`, `tools/GENERATED_TARGET.md` | All 38 requirement IDs have evidence; normal discovery includes the 5,000 edge methods |
| Native builds and exact-package acceptance | [Worker PR #1](https://github.com/danieladegoede-ai/coco/pull/1) | Windows x64, Linux x64 and macOS arm64 pipelines, provenance and extracted-ZIP tests implemented |
| Manual and declarations | `release/group-2.tex` | Five-page LaTeX manual and both declarations implemented; A33 signatures and actual upload remain personal actions |

Hosted CI has executed real Windows/Linux source tests and all three native
platforms; the old zero-job startup failures in dated packets are historical.
Require green checks and matching provenance for the current head before
using its release candidate. Do not reinterpret historical failures as current
or mix artifacts from different commits.

## First actions for an AI

1. Read root AGENTS.md, this file, your personal packet, shared interfaces and
   handoff/acceptance. Read the relevant original 2026 course sheets when
   available; private course files do not belong in Git.
2. Inspect `git status --short --branch`, recent commits and source files. Do
   not reset, clean, checkout over, or overwrite someone else's uncommitted work.
3. Fetch origin and read your issue and its dependencies. With authenticated gh:

   ```sh
   git fetch origin
   gh issue view ISSUE --repo RudolphLamp/coco
   gh pr list --repo RudolphLamp/coco --state open
   ```

4. Identify one concrete owned issue to implement. State which base branch,
   API inputs and expected outputs you will use. Check that required source
   files actually exist on that base; do not invent placeholder imports on main.
5. If foundation/names are merged, branch from updated main. If development
   needs pending APIs, explicitly branch/stack on the required remote feature
   branch after checking its current PR state. Name that parent in the new PR.
   Do not cherry-pick another member's whole feature into unrelated work or
   recreate the shared models under a second API.
6. A blocked issue permits independent fixtures, data-model tests, harness
   scaffolding and development on an explicit parent branch. It cannot be
   declared fully integrated until real dependencies pass and merge. Clearly
   label stub/model-only evidence; replace stubs at the handoff boundary.
7. Implement code, focused tests and documentation together. Continue ordinary
   authorized work without repeated permission requests. Raise only material
   missing requirements or breaking cross-owner interface changes.

If gh access is unavailable, the personal packet includes the task requirements
and links. Read available source locally, proceed with independent owned work,
and state exactly which live dependency facts could not be verified.

## Shared scope and output constraints

- Keep the existing lexer/parser and exact 2026 grammar. Every token, including
  the last, ends with a supported separator. The literal $ is never SPL input.
- Semantic-valid cases must declare variables and obey call/type rules. P1
  syntax-only fixtures can contain semantic errors; preserve them under a
  deliberate frontend-only test boundary when #31 changes the default pipeline.
- Variables resolve to the nearest current/ancestor declaration. A21 forbids
  sideways sibling/cousin lookup. Parameters/body locals share duplicate scope.
- Calls use only the immediate F_DECL of the caller P. No overloading or
  direct/indirect recursion. Branches and loops create no declaration scope.
- Internal names represent declaration identity. Keep original tree/XML intact;
  use semantic side maps and actual source tokens for source spans.
- Whole-tree numeric restrictions include uncalled functions and returns. Both
  mod and div require the exact message `A float-integer-conflict might perhaps be possible`.
  Any mod forbids decimal NUM anywhere. Do not mistake string text for operators.
- Backend code uses one selected numeric mode, structural storage/label IDs,
  one main, declaration hoisting, comparison/goto control flow and required
  function inlining. Keep code-mine templates non-executable.
- Only a successfully checked program can reach final code generation. Only a
  validated successful target is published. Protect input before output cleanup.

## Final decisions: no consultation dependency

The Speaker instructed completion without tutor consultation and appointed
this AI as the main technical reviewer. Apply the eight
[final release decisions](../../release/P2_RELEASE_DECISIONS.md). Their evidence
is recorded in the main review; no pending tutor question blocks implementation.
Dated personal packets and schedules below are historical allocations, not
new instructions to obtain consultation or repeat completed source work.
A33's genuine personal signatures and First Class upload remain personal actions.

## Internal working targets

These are planning targets, not official cutoff times. Report slippage and
remaining tests honestly; do not mark unfinished work complete to meet a date.

| Date | Desired integration result |
| --- | --- |
| 18 Oct | Foundation/names review, numeric/type and IR/template work underway |
| 19 Oct | Arithmetic plus first target compile/run; type-rule coverage |
| 20 Oct | Historical integration target: Boolean/loop tests and call integration |
| 21 Oct | Complete nested/repeated-call pipeline |
| 22 Oct | Feature freeze with full required source-based semantic/execution matrix |
| 23 Oct | Tested native release candidate from one recorded commit |
| 24 Oct | Four-member review, both personally signed declarations, early verified upload |
| 25 Oct | Official final date; confirm the portal hour in advance |

## Completion means evidence

Use [the common handoff format](90_HANDOFF_AND_ACCEPTANCE.md). A coding AI
should finish with an owned implementation, meaningful tests, a pushed branch
and reviewable PR, not just a plan. Final release completion additionally needs
real native execution, correct target behavior, manual/signatures and the
Speaker's verified upload. Never fabricate those external actions.
