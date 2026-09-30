# u21448842 - CLI, generated testing and executable

## Objective

Provide the public front-end command, automated valid/invalid program
generation, full black-box testing and a runnable submission build.

## Owned paths

```text
src/spl_frontend/__init__.py
src/spl_frontend/__main__.py
src/spl_frontend/diagnostics.py
src/spl_frontend/compiler.py
src/spl_frontend/cli.py
tools/generate_valid_spl.py
tools/mutate_spl.py
tools/black_box_test.py
tests/integration/
tests/generated/
tests/test_cli.py
```

Do not reimplement lexer, parser, tree or XML internals. Use their public
contracts or small temporary fakes.

## CLI and pipeline checklist

- Implement the shared structured diagnostic base classes.
- Support the approved no-argument/default and optional-path behaviour.
- Default to `SPL.txt` input and `tree.xml` output.
- Coordinate source load, tokenization, parsing, validation and XML writing.
- Return zero only after a fresh valid `tree.xml` has been published.
- Return non-zero for usage, I/O, lexical, syntax and internal failures.
- Print expected errors without a Python traceback.
- Send errors to standard error.
- Ensure a failed run cannot leave stale output that appears successful.
- Provide `python -m spl_frontend` during development.

## Valid-program generator

- Generate from `SPL_PROG` using every grammar production.
- Use deterministic seeded randomness.
- Enforce maximum recursion depth, node count and instruction count.
- Produce valid lexical forms and required token separators.
- Never emit literal `$`.
- Record the random seed with each generated case.
- Support a deterministic mode that guarantees production coverage.

## Invalid-program mutator

Starting from known-valid programs, create one fault at a time:

- remove a separator token;
- remove or replace a semicolon, colon, brace or parenthesis;
- remove a required keyword;
- insert an unexpected token;
- corrupt a name, number or string;
- truncate input at selected grammar positions; and
- append trailing input.

Store the mutation description and expected failure phase/location range.

## Black-box harness

- Run the same command the tutors will run.
- Use a fresh temporary directory for every case.
- Copy only the executable and required input.
- Verify exit status, standard error and output-file behaviour.
- Parse successful XML and check the basic structural invariants.
- Test repeated runs and valid-after-invalid/invalid-after-valid sequences.
- Test missing, unreadable and non-ASCII input.
- Save a concise failure report containing command, seed and input.

## Executable build

- Confirm the tutor's operating system, CPU, command and archive format before
  freezing the build.
- Build on the target operating system, not on macOS for a non-macOS target.
- Use a reproducible build command and record the Python/tool versions.
- Test on a clean machine without the repository or development environment.
- Create a checksum, upload early, download again and retest the downloaded
  artifact.
- Do not commit the executable to the source branch.

## Acceptance

- CLI works against fakes before integration.
- Generator terminates for every seed and covers every production.
- Mutations are single-fault and reproducible.
- Full pipeline passes handwritten and generated cases.
- Packaged executable passes the clean-machine black-box checklist.
