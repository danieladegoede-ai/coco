# COS341 SPL Front End - Group 2

This repository is a clean starting point for Group 2's COS341 front-end
assessment.

## Current scope

We are working only on the SPL front end this week.

The strict submission deadline is **Wednesday, 30 September 2026**. Missing the
deadline means receiving zero for the front-end assessment.

The front end must:

- read a plain ASCII input file named `SPL.txt`;
- recognise valid SPL tokens and reject malformed tokens;
- check the complete SPL grammar;
- give a meaningful syntax error with a helpful hint for invalid input; and
- write a browser-readable `tree.xml` containing the complete syntax tree for
  valid input.

No work outside the front-end assessment belongs in this repository right now.

## Confirmed decisions

### Python

The implementation language is Python 3.11 or later. The final submission must
still be packaged as a runnable executable for the tutors' target computer.
The exact operating system, processor architecture, upload format and run
command must be confirmed before the release is built.

### Separate lexer and parser

The front end will use a separate lexer followed by a predictive
recursive-descent parser.

The lexer owns character-level rules, token boundaries and source positions.
The parser owns grammar rules, lookahead, syntax errors and tree construction.

The supplied grammar has two shared-prefix decisions:

- after a user-defined name in an instruction, `=` starts an assignment and
  `(` starts a function call;
- after a user-defined name in a term, `(` starts a function call and otherwise
  the name is a variable term.

These decisions can be handled with controlled lookahead while the generated
syntax tree still uses the original grammar's node names.

## Important specification details

- Every token must end with the specification's `blank_space` delimiter.
- The main lexical categories are `NUM`, `USER-DEFINED-NAME` and `STRING`, plus
  the reserved keywords and punctuation shown in the grammar.
- The `$` in grammar Rule 0 is only an end-of-file meta-symbol. It must not
  appear in `SPL.txt`, and the parser must not try to consume it from the file.
- Nullable productions must be handled without consuming an input token.
- Parsing succeeds only after the entire input has been accepted.

## Required syntax-tree output

For valid input, the program must create `tree.xml`.

The tree contains:

- one root node with a unique ID, the start symbol as its contents and an
  ordered list of immediate child IDs;
- inner nodes with unique IDs, grammar non-terminals, ordered child IDs and a
  parent ID; and
- leaf nodes with unique IDs, consumed terminal-token contents and a parent ID.

Every ID must be globally unique. Parent and child references must agree, and
the XML must be well formed and readable in a web browser.

## Testing approach

The test suite will contain handwritten boundary cases and a small grammar-based
program generator.

The generator will create syntactically valid SPL programs from `SPL_PROG` with
depth and size limits. Every generated valid program must parse successfully.
Copies of valid programs will then be changed one fault at a time so that the
syntax-error handling can be checked at known locations.

The final executable must be tested as a black box on a clean copy of the
tutors' target environment. The tutors will not inspect the source code or
rebuild a broken submission.

## Repository layout

```text
.
|-- src/             Front-end source code will go here
|-- tests/           Unit, integration and generated test cases will go here
|-- .editorconfig    Shared basic editor settings
|-- .gitignore       Local and generated files excluded from Git
|-- pyproject.toml   Minimal Python project information
`-- README.md        Confirmed front-end scope and working rules
```

The source and test folders are intentionally empty. Implementation files will
be added only after the four group members approve the work split.

## Basic setup

1. Install Python 3.11 or later.
2. Clone this private repository.
3. Create a short-lived branch for the agreed task.
4. Add the implementation and tests for that task together.
5. Open a pull request and ask another group member to review it.

Do not commit `SPL.txt`, `tree.xml`, Python caches, virtual environments,
packaged executables or private course material.

## Definition of done for the front end

The front end is ready only when:

- all token categories and grammar productions have positive tests;
- invalid tokens and syntax mistakes have negative tests;
- valid input always produces a fresh, structurally correct `tree.xml`;
- invalid input cannot leave an old or partial `tree.xml` that looks current;
- `$` is never required in the source file;
- the full generated and handwritten corpus passes;
- the packaged executable runs on a clean target machine; and
- the uploaded copy is downloaded and tested before the deadline.

## Questions that still need official answers

- Which operating system and processor will run the executable?
- What exact command will the black-box tester use?
- Must the program always read `SPL.txt` from the current directory?
- Is there an exact XML tag structure or sample output to follow?
- How must nullable grammar productions appear in `tree.xml`?
- May end-of-file directly terminate the last token, or is a final
  `blank_space` always required?
- Where and in what format must the executable be uploaded?

No GitHub implementation issues will be created until the team agrees on the
front-end work split.
