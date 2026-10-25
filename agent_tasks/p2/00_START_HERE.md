# Start here: Group 2 Phase 2 AI instructions

Updated 18 October 2026 at the Speaker's request. These guides supersede the
September frontend-only task allocation. The goal is a **1st Class** COS341
2026 submission: Parts **2a, 2b, 3a and 3b**, including correct executable target
generation, for up to **6/6 P2 points**. P1 earned full marks and stays covered.
The final date is **Sunday 25 October**; no exact cutoff hour is confirmed.

## Choose the member, then the issue

| Member / GitHub | Work order | Packet |
| --- | --- | --- |
| Rudolph / u20598425 / RudolphLamp | Review existing #21/#22/#23, then #36 release work | [Rudolph](10_u20598425_foundation_names_release.md) |
| Kuda / u20620111 / Kuda21 | #24 numeric scan and #32 generator can start independently on contracts; #25 types; #33 semantic negatives | [Kuda](20_u20620111_types_numeric_tests.md) |
| Cherise / u21434019 / CheriseHeyl | #26 IR; #27 arithmetic; #28 Booleans/loops; #34 executable verification | [Cherise](30_u21434019_codegen_verification.md) |
| Michele / u21448842 / michey-n | #29 templates; #30 inlining; #31 integration; #35 native release | [Michele](40_u21448842_inlining_driver_release.md) |

Each issue has one primary owner and a named reviewer. Reviewing does not
transfer implementation ownership. Work is tied to issue paths, not exclusive
ownership of a whole test directory. Do not create overlapping implementations
or take another member's work because its module has not merged yet.

## What exists, and where

Snapshot at this refresh; verify live status before editing:

| Work | Location | Meaning |
| --- | --- | --- |
| Complete P1 source | main, baseline 0be22db | Existing lexer/parser/XML/CLI regression baseline |
| #21/#22 foundation | [PR #37](https://github.com/RudolphLamp/coco/pull/37), feat/u20598425-p2-foundation | Implemented for review; 320 local tests passed at original handoff |
| #23 name analysis | [PR #38](https://github.com/RudolphLamp/coco/pull/38), feat/u20598425-p2-names, based on #37 | Implemented for review; 363 local tests and 10/10 CLI cases passed |
| #24-#35 passes/tools | Assigned issues; inspect live branches | Requirements, not an assertion of implementation |
| #36 final release | Assigned issue; final gates pending | Drafting is possible; release waits on tested native artifact and real signatures |

The reported checks used macOS arm64 Python 3.14.0. Hosted Actions showed
startup_failure with zero jobs, including the #38 branch. Windows/Linux and
Python 3.11 runtime passes were not established by those local runs. Treat
missing CI jobs as unverified, not successful. Do not make speculative account
changes or claim a billing diagnosis without evidence.

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

## Decisions still awaiting tutor confirmation

See [the exact D01-D08 table](05_SHARED_INTERFACES.md#tutor-decisions).
Do not block confirmed lookup/arithmetic/IR work on unrelated questions, and
do not present a provisional policy as an official language rule. Isolate each
proposal so an actual answer can change one boundary and its tests.

## Internal working targets

These are planning targets, not official cutoff times. Report slippage and
remaining tests honestly; do not mark unfinished work complete to meet a date.

| Date | Desired integration result |
| --- | --- |
| 18 Oct | Foundation/names review, numeric/type and IR/template work underway |
| 19 Oct | Arithmetic plus first target compile/run; type-rule coverage |
| 20 Oct | Tutor consultation answers recorded; Boolean/loop tests and call integration |
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
