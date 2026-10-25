# P2 integration, review and release evidence

Read with the start guide and personal packet. This is the shared P2 process;
the older ../90_integration_and_release.md and frontend checklist remain P1
records. Nothing here changes the actual state of a GitHub issue or review.

Release update, 25 October: the Speaker designated this AI as the main
technical reviewer and instructed completion without consultation. Apply the
[final release contract](../../release/P2_RELEASE_DECISIONS.md). This supersedes
the earlier consultation/named-peer technical-review allocations below; it does
not supply the personal signatures or real upload required by A33.

## Integration order and ownership

| Boundary | Provider | Consumer | Evidence required |
| --- | --- | --- | --- |
| Models/tree/source maps (#21/#22) | Rudolph | All members | Compatible real-tree/round-trip fixtures; affected-owner review |
| Name bindings (#23) | Rudolph | Kuda types, Michele templates, Cherise references | N01-N10 and exact symbol/rename identities |
| Numeric facts/types (#24/#25) | Kuda | Cherise backend, Michele driver/inliner | T01-T10; known checked root and one numeric mode |
| IR/writer (#26) | Cherise | Cherise generation, Michele templates/inliner | Compilable skeleton, structural refs, clone/remap and label validation |
| Terms/Booleans (#27/#28) | Cherise | Michele call expansion/driver | Arithmetic behavior, truth tables, all four loops, public call hook |
| Templates/inlining (#29/#30) | Michele | Final driver/backend | Fresh call storage/labels; nested captures and returns |
| Full CLI (#31) | Michele | Semantic/executable tests | Safe phase errors/output lifecycle and real final command |
| Generator/negative matrix (#32/#33) | Kuda | Cherise verification, Michele native gate | Independent known outcomes, parser-valid negatives and reproducible seeds |
| Executable-target tests (#34) | Cherise | Michele release, Rudolph manual | Compile/run evidence and requirements matrix |
| Native artifacts (#35) | Michele | Rudolph final release | Tested exact artifacts, hashes/platform/toolchain/commit |
| Manual/declarations/upload (#36) | Rudolph + personal member actions | Tutors | Accurate launch, both declarations, exact ZIP and verified upload |

Do not introduce a circular gate: #33/#34 finish their source-based corpus and
harness, then #35 reruns that same corpus against the package. They do not wait
for the final native binary before providing runnable tests to its owner.

## Branch and review rules

1. Check live main and dependencies. Keep pending foundation/name code on
   explicit parent branches; never merge someone else's pending feature merely
   to make your branch look independent. Update parents through normal review.
2. Own one concrete issue per focused PR where practical. Name all shared-file
   changes and affected owners. Preserve other members' uncommitted work.
3. Base a stacked PR on its actual feature parent and explain merge order.
   Retarget/reconcile after that parent merges. Preserve tests, approved
   interfaces and useful review history while resolving conflicts.
4. Resolve findings from the Speaker-designated main technical review. Preserve
   actual review evidence; no technical review counts as another member's
   personal signature or consent under A33.
5. Check dependency results with real modules before claiming integration.
   Local success is platform-specific; unavailable or zero-job CI is unverified.
   Do not bypass branch checks, change repository settings or conceal failures.
6. Preserve required review/test gates for feature merges. The Speaker's direct
   documentation request does not authorize pretending feature PRs were reviewed.

## Required verification

Use Python >=3.11; record actual interpreter/platform. From the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests tools
PYTHONPATH=src python3 tools/black_box_test.py
git diff --check
```

Also run the personal packet's focused suites. Pending modules cannot be
imported on a P1-only base: choose the proper dependency branch or label a
fixture-only check honestly. Do not delete existing tests to get green output.

For target behavior, retain four separate outcomes: compiler result, target
compiler result, target execution result and output comparison. Use fresh
temporary directories, compile/run timeouts and initialized bounded programs.
Use exact integers/strings and documented float tolerance/format policy.
Record actual target compiler/version and commands; C++17 is the D01 release choice.

Every relevant backend test must compile and execute the target. Substring
snapshots cannot establish arithmetic, Boolean, capture or return correctness.
Structural checks tokenize executable code and ignore strings/comments/code
mine; detect raw SPL names, runtime SPL calls, duplicate/missing labels, extra
main functions and prohibited executable ELSE/composition.

## Minimum end-to-end anchors

- Names: nearest ancestor versus sibling/cousin; same-spelling distinct
  declarations; own-parameter masking, duplicate domains and direct-only calls.
- Types: numeric versus procedure call contexts, numeric return/arguments,
  empty productions and uncalled invalid functions.
- Numeric: both mod/div exact conflict message; decimal plus mod across
  separate/uncalled bodies; div(5,2)=2.5 and mod(5,2)=1 in executable output.
- Arithmetic/output: nested terms, self-reading assignment, exact strings,
  consecutive print order, comments/nop with no runtime effect.
- Booleans: full and/or/not truth tables; nested not/or false fall-through
  regression; both branches; side effects under the recorded evaluation policy.
- Loops: pre/post while and until, zero-iteration pre-tests, guaranteed first
  post-test execution, initially true/false and terminating repeated iterations.
- Calls: zero/multiple actuals per recorded arity policy, nonzero argument copy,
  earlier capture surviving later argument effects, calls in all numeric
  contexts, nested return calls, repeated function expansions with loops.
- Captures: child writes to its current parent's local, then a second parent
  invocation proves storage was remapped to the new instance. Preserve globals.
- Driver/package: default/explicit paths, spaces, input/output alias safety,
  valid-invalid-valid sequences across every phase, no traceback/stale target,
  and source/package agreement on identical fixture IDs/seeds.

The acceptance matrix covers all 38 planning IDs: N01-N10, T01-T10, G01-G10,
F01-F08. They are planning IDs, not an invented official marking rubric. Map
each to concrete case IDs, expected results and actual evidence; expose gaps.

## Required issue/PR handoff

Copy and fill with actual values:

```text
Owner/student:
Issue and requirement IDs:
Branch / base branch / parent PR:
Commit and PR URL:
Owned paths changed:
Public API inputs -> outputs and diagnostics:
Dependency versions/commits actually exercised:
Focused/full check commands, counts and results:
OS / Python / target compiler / package platform:
Concrete successful and rejected example:
Source spans or XML-only node behavior:
Deterministic state/output and valid-invalid-valid evidence:
Tutor proposals used; confirmed answers with date/source if available:
Known gaps, unrun checks and remaining human gates:
Named reviewer and downstream handoff:
```

Push the work so another member can inspect it; local-only work is not a
handoff. Update the linked issue/tracker when authorized to report there. Do
not send external messages on another person's behalf without authorization.

## Native and final-release gate

Build for each configured supported OS/CPU on its own platform, with pinned
packaging versions and a recorded source commit. A Windows .exe needs a native
Windows build/test; a Mac test does not prove it launches there. A supplemental
Linux file is group-2 with no extension if agreed. Document any target-compiler
dependency separately from the dependency-free packaged compiler executable.

Run the same semantic rejection and target-execution corpus against the exact
packaged binary outside the checkout. Record filename, size, SHA-256, platform,
build tools and full results. Only tested artifacts can enter the final ZIP.

Rudolph's manual must match those exact filenames, outputs/statuses and commands.
It contains two declarations: unanimous 1st Class category agreement, and each
member's awareness/approval of all final ZIP contents. **All four personally
sign both declarations**: eight signatures in total. Templates, typed names
and AI-generated signatures do not satisfy that personal-action requirement.

Another member follows only the final manual from the extracted ZIP, runs a
valid example through generated target execution, and confirms a semantic
failure leaves no misleading target. Inspect every final PDF page. Exclude
private sheets, caches, scratch inputs, old builds and planning PDFs.

The Speaker uploads **only to the 1st Class slot**, after the actual group
approval/signature gates and before the cutoff displayed in that slot. Never upload in both
categories. Download the submitted ZIP, compare hashes, retest its extracted
binary and save the receipt/slot evidence outside the source repository.
Final changes after approval require accurate renewed member review.
