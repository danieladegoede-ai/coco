# Integration and release plan

## First agreement

Before feature coding, approve:

- token fields and token types;
- token-stream methods;
- diagnostic fields and rendering;
- tree node fields and builder methods;
- parser and XML function signatures; and
- CLI command, defaults and exit behaviour.

This is the only short shared dependency. Keep it small and merge it first.

## Parallel development

Each owner works against fakes:

- Lexer owner needs only `SourceFile` and token contracts.
- Parser owner uses manually constructed tokens and a fake/real tree builder.
- Tree/XML owner creates trees directly without parser input.
- CLI/testing owner uses fake tokenize/parse/write functions.

## Integration order

1. Merge approved contract definitions and empty package structure.
2. Merge tree/XML and lexer independently after their unit tests pass.
3. Merge parser after its manual-token tests and tree validation pass.
4. Connect source -> lexer -> parser -> validator -> XML in `compiler.py`.
5. Run handwritten integration cases.
6. Run generated valid cases.
7. Run one-fault invalid cases.
8. Build and test the target executable.

## Review pairing

- Lexer and parser owners review each other's boundary assumptions.
- Tree/XML and CLI/testing owners review output lifecycle and black-box
  behaviour.
- The Speaker checks integration contracts and confirms tutor answers are
  recorded.

Reviewing does not transfer ownership. The original owner fixes findings.

## Merge rules

- Pull the latest `main` before opening a pull request.
- Keep each pull request inside the owned paths where possible.
- Shared-file changes must name every affected owner.
- Include tests with implementation.
- Do not merge red or unrun tests.
- Do not combine formatting changes with functional changes across the whole
  repository.
- Resolve interface disagreements before integration, not during the final
  release build.

## Output safety

The integrated pipeline must never publish `tree.xml` until all stages succeed.
Recommended order:

```text
read -> tokenize -> parse -> validate tree -> serialize temporary XML
-> validate XML -> atomically replace tree.xml
```

On any failure, return non-zero, print one useful diagnostic and ensure no
partial output is presented as the result of that run.

## Release gate

All four members must independently confirm:

- executable starts on the target environment;
- valid input returns zero and writes fresh XML;
- invalid input returns non-zero and does not publish misleading XML;
- `$` is absent from test sources;
- generated and handwritten suites pass;
- downloaded submission matches the local checksum; and
- proof of submission is saved outside the repository.
