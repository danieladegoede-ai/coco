# Generated-target acceptance runner

Run the ten hand-computed backend anchors from the repository root:

```sh
PYTHONPATH=src python3 tools/test_generated_target.py \
  --manifest tests/fixtures/codegen/acceptance/cases.json \
  --target-compiler /usr/bin/c++ --artifacts build/target-failures
```

The default compiler subprocess uses the existing lexer/parser, source map,
name/type checks, `generate_target(CheckedProgram)` and `write_target` APIs.
It is an adapter for the algorithm backend. It preserves `CallEmitter` and
does not implement function inlining or claim final CLI/package integration.
C++17, short-circuit evaluation and output formatting remain the proposals
recorded in the shared task packet. Numeric output uses C++ stream defaults;
the curated manifest has independently specified exact output strings. Part 3a
requires `int` or `float` storage; real constants carry an `f` suffix so
arithmetic and literals follow binary32 precision. Terms, Booleans and nested
control flow lower with work stacks. Native integer/float ranges apply;
overflow and division by zero do not have an invented SPL rejection rule.

To test a downstream compiler, pass `--compiler-command` as a JSON argv array.
It runs without a shell in a fresh directory containing `SPL.txt` and must
produce `program.cpp`. The optional `{input}` and `{target}` placeholders become
absolute paths. Use absolute executable/script paths for reproducible runs.

Each report separates compiler-process status, structural checks, C++
compilation, execution and output comparison. Failures retain the source,
target if produced, expected output, per-stage logs, JSON metadata/report and
`reproduce.sh` under the artifact directory. Run `sh reproduce.sh` inside a
saved failure directory to replay with the same timeouts. For a saved target
alone use `--source input.spl --expected expected.stdout --target program.cpp`.

The inspector tokenizes the restricted generated dialect and ignores quoted
strings, raw strings, comments and preprocessor directives, including C++ line
splicing. Native compilation remains necessary to validate general C++ syntax
and names outside the generated SPL namespaces. F01-F08 remain downstream
inlining gates in the requirement matrix; a backend pass does not
establish their completion.
