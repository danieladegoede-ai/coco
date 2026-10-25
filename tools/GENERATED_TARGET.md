# Source acceptance handoff

These commands verify the integrated compiler before native packaging or the
submission manual. They do not build the packaged SPL executable.

```sh
PYTHONPATH=src python3 tools/test_semantic_acceptance.py \
  --manifest tests/fixtures/semantics/cases.json \
  --artifacts build/semantic-failures
PYTHONPATH=src python3 tools/test_generated_target.py \
  --manifest tests/fixtures/codegen/acceptance/cases.json \
  --execution-timeout 5 --artifacts build/acceptance-failures
```

The semantic manifest contains 74 parser-valid cases: 28 negatives with valid
partners and recorded token edits, and 46 legal boundaries/partners. Each case
records requirement IDs, confirmed/provisional policy, expected phase/status/
code, explanation and independently selected source ranges. The semantic runner
uses the real CLI in fresh directories with an explicit filename containing
spaces and pre-existing stale outputs. It checks diagnostics, source preservation
and the successful/rejected XML/target lifecycle. Failures retain source, logs,
commands and a portable `python reproduce.py` replay.

The target manifest contains 31 exact-output fixtures. B01-B10 are supplemental
algorithm anchors; C cases cover function/argument/capture behavior. The
separate `planning_anchors.json` preserves the original E01-E10 meanings from
the plan: E02-E05 are semantic errors, while E01/E06-E10 have executable output.
No expected rejection is passed off as a successful target execution.

The default target runner enters the actual public CLI, including names/types,
inlining and protected output publication. It then inspects executable C++,
compiles it and runs it with separate timeouts and status/stdout/stderr fields.
Its inspector ignores comments, code mines and quoted/raw string data, and
checks main/return count, labels, generated storage, raw SPL names, runtime SPL
calls and forbidden ELSE/Boolean composition. Native compilation remains the
syntax/name check for C++ beyond that restricted dialect.

All 38 original N/T/G/F planning IDs map to actual test methods and semantic/
target case IDs in `requirements.json`. Tests also compare 16 seeded programs
(integer and float modes) against both generator facts and the independent
reference evaluator, plus hand-calculated float/remainder/equality cases.
Fault-sensitivity tests deliberately introduce wrong Boolean destinations,
reversed formal copies, stale parent captures and reused labels; these must
fail the harness. No required case is silently marked blocked or skipped in
its CLI summary.

A failure saves source, target if present, expected stdout, per-stage logs,
JSON metadata/report, commands and seed under its artifact directory. The
portable replay is `python reproduce.py`; `sh reproduce.sh` remains available
for target failures. Unexpected corpus/generator failures use ignored build
folders so tests retain the evidence. The source CI workflow requires a target
compiler and retains failure artifacts when jobs actually start.

For the later #35 package rerun, pass `--compiler-command` as a JSON argv array
to either runner. It runs without a shell in a fresh directory, accepts optional
`{input}`/`{target}` placeholders, and must produce the documented output names.
Use absolute executable/script paths; paths with spaces stay individual argv
items. Both runners return nonzero for any failed required case. This interface
is ready for package/source comparison, but no package result is claimed here.

Runtime int/float ranges and default stream formatting apply; the oracle models
binary32 rounding and exact output for the bounded initialized corpus. D01-D08
remain provisional: target cases list their selected runtime policies, and
source cases depending on unanswered namespace/return questions are tagged.
The manifests are planning/test evidence, not an official marking rubric or
an invented tutor approval.

## Expanded 5,000-case audit matrix

The additional deterministic edge corpus lives in `tests/edge5000/`; the
review inventory is `tests/fixtures/edge5000/index.jsonl`. Every method has a
stable EDGE00001–EDGE05000 ID, a distinct source fingerprint, explicit expected
stdout or failure code/location, a profile and requirement tags. These 5,000
sources do not repeat the earlier SYS0001–SYS0500 corpus. A matrix case can
cover multiple layout/control/operand axes; it is not 5,000 distinct language
productions. The accompanying ten `test_numeric_boundaries` methods test safe
int32/binary32 representation anchors under the recorded D05 interpretation.

```sh
# Full coverage, retained tests serially then the edge class in bounded threads:
python3 tools/run_edge_5000.py --suite all --workers 6
# Edges only; real public CLI + native target execution on successful cases:
python3 tools/run_edge_5000.py --suite edges --workers 6
# One case, with retained input/stage evidence on failure:
python3 tools/run_edge_5000.py --ids EDGE01501
# CI partition: repeat for shard-index 0, 1, 2 and 3:
python3 tools/run_edge_5000.py --shard-count 4 --shard-index 0 --workers 2
# Regenerate review inventory after an intentional factory change:
python3 tools/run_edge_5000.py --write-inventory
```

Normal `PYTHONPATH=src python3 -m unittest discover -s tests -v` includes all
methods too, and runs them serially. The bounded runner executes the exact
same unittest methods, with temporary directories/subprocess cwd per case;
legacy tests run serially because some change their process cwd. Never thread
the historical suite. JSON reports include tested IDs, skips, separate CLI/
native/API counters, per-case results, toolchain and timings. Failures retain
source, expected results, commands/statuses/logs, positive partners where
applicable and a reproduction command in `build/edge5000-failures/EDGE00001/`.
A missing C++ compiler or unavailable required filesystem operation is reported
as an actual failure; a source-only result is not silently called a native pass.

See [the expanded audit](../agent_tasks/p2/P2_FULL_AUDIT_20261025.md) for the
source review, exact counts, interpretations and remaining release gates.
