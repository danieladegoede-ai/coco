# P2 baseline and verification

> Release instruction, 25 October: the Speaker finalized D01-D08 without
> tutor consultation and appointed this AI as main technical reviewer. Use
> [the final release contract](../../release/P2_RELEASE_DECISIONS.md). The dated
> allocations/proposals below are historical and add no consultation or
> named-peer technical-review gate. A33 personal signatures/upload remain real
> personal actions.

17 October 2026, #21/#22, branch `feat/u20598425-p2-foundation`.

## Provenance

- Fetched origin. Main was `0be22dbdf614a31a1936f32fec5aede81959ede8`.
- Created separate worktree `COCO ass/coco-p2-foundation`; preserved the old
  docs checkout and submitted P1 files/ZIP.
- All 14 main `src/spl_frontend/*.py` modules matched the submitted-build
  support checkout at `1e588a9` before P2 edits.
- Differences in that support checkout are release CI/packaged-edge support,
  not missing lexer/parser code. Native release reconciliation belongs to #35.
  This branch adds a source-test workflow for its own PR.
- No private tutor input, course PDF or packaged executable is added here.

## Baseline and checks

Before edits: **267 tests passed**, macOS/Python 3.14. After the foundation:
**320 tests passed**, including 53 new focused/integration tests; compileall
passed and all **10/10 source CLI black-box checks** passed. Native source CI
results are recorded in the PR. These checks do not establish that the pending
P2 passes or a new native packaged compiler already exist.

The private six-case P1 tutor ZIP is checked locally: T1/T2/T3 accepted, T4
lexical failure, T5/T6 syntax failure. T2/T3 are frontend fixtures and may be
semantically invalid later. Check default/explicit CLI paths, deterministic
XML and the existing stale-output behavior independently.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests tools
PYTHONPATH=src python3 tools/black_box_test.py
```

On the Speaker's Mac use `/opt/homebrew/bin/python3` (3.14); system Python 3.9
does not meet the requirement. Source CI uses Python 3.11 on Ubuntu/Windows.
#35 owns native compiler packaging and the eventual target-execution gate.

## Downstream handoff

Integration fixtures demonstrate resolved annotations, typed snapshot creation,
codegen access to mode/internal names, and ordered function parameters/body
scope for inlining. In-memory/XML-round-tripped results agree and P1 XML remains
byte-identical. These explicit fixtures are not the actual name/type passes
or evidence that their owners reviewed the contracts.

Human review and consultation remain unchecked in the decision record/tracker.
The PR prepares usable interfaces now; #23-#35 implement the remaining compiler.
