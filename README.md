# COS341 SPL Front End - Group 2

This repository contains Group 2's COS341 SPL front end.

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
- The final token also needs a separator. A bare end-of-file does not count as
  `blank_space`; use a trailing space or newline in `SPL.txt`.
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
`-- README.md        Front-end usage and working rules
```

The source reader, lexer, parser, syntax tree, XML writer and development CLI
are integrated. Packaging the required executable is a separate release task.

## AI-assistant work packets

The root [`AGENTS.md`](AGENTS.md) file contains the rules that every coding
assistant must follow. Detailed front-end work packets are stored in
[`agent_tasks/`](agent_tasks/README.md).

The team approved `1A, 2A, 3A, 4C` and the allocation on 22 September 2026.
Each member and their AI assistant must read the
[`approved decisions`](agent_tasks/00_team_decisions.md), shared contracts, SPL
reference and that member's own work packet before changing code.

These files remain the detailed source of truth behind the approved GitHub
issues.

Approved implementation issues:

- [`#8` - u20598425: syntax tree and XML](https://github.com/RudolphLamp/coco/issues/8)
- [`#9` - u20620111: source reader and lexer](https://github.com/RudolphLamp/coco/issues/9)
- [`#10` - u21434019: parser and syntax diagnostics](https://github.com/RudolphLamp/coco/issues/10)
- [`#11` - u21448842: CLI, generated tests and executable](https://github.com/RudolphLamp/coco/issues/11)

## Basic setup

1. Install Python 3.11 or later.
2. Clone this private repository.
3. Create a short-lived branch for the agreed task.
4. Add the implementation and tests for that task together.
5. Open a pull request and ask another group member to review it.

Do not commit `SPL.txt`, `tree.xml`, Python caches, virtual environments,
packaged executables or private course material.

## Run the integrated front end during development

From the repository root, create `SPL.txt` in the directory where you will run
the command. The smallest valid program is `: : `, with a space after each
colon. Then run:

```sh
PYTHONPATH=src python3 -m spl_frontend
```

You may pass one input path instead of using `SPL.txt`:

```sh
PYTHONPATH=src python3 -m spl_frontend path/to/input.txt
```

Successful runs return zero and write a fresh `tree.xml` in the current
directory. Errors are printed to standard error and return a nonzero status.
The driver removes an old `tree.xml` before attempting a new compilation, so
an input failure does not leave the previous result looking current. Do not
put the literal `$` at the end of `SPL.txt`; it is only a grammar meta-symbol.
These Python commands are for development; the submission executable must be
tested separately on the tutors' target platform.

## Run the syntax tree and XML writer

Run this example from the repository root with Python 3.11 or later. It builds
a small tree in memory, validates its structure, and writes `tree.xml` in the
current directory:

```sh
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path

from spl_frontend.tree import SyntaxTree
from spl_frontend.xml_writer import write_tree

tree = SyntaxTree()
root = tree.add_root("SPL_PROG")
program = tree.add_inner("P", root.node_id)
tree.add_leaf(":", program.node_id)

tree.validate()
write_tree(tree, Path("tree.xml"))
print(Path("tree.xml").resolve())
PY
```

Open the printed path in a browser to inspect the XML. The example shows the
tree/XML API; it is not a complete SPL program. The parser will supply the
grammar nodes and terminal lexemes during a normal compilation.
`SyntaxTree` assigns IDs and updates ordered child links automatically; callers
should not edit `child_ids`. `write_tree` validates again and atomically replaces
the output file. The output directory must already exist. Do not commit the
generated `tree.xml`.

## Run the tree and XML tests

From the repository root, using Python 3.11 or later:

```sh
PYTHONPATH=src python3 -m unittest tests.unit.test_tree -v
PYTHONPATH=src python3 -m unittest tests.unit.test_xml_writer -v
PYTHONPATH=src python3 -m unittest tests.integration.test_tree_xml -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests tools
```

The tree/XML integration tests construct trees directly. The full suite also
tests the integrated CLI, generated programs and repeated-run output safety.
Run the development black-box harness with:

```sh
python3 tools/black_box_test.py
```

For the larger edge corpus and deterministic grammar coverage case:

```sh
PYTHONPATH=src python3 -m unittest tests.integration.test_edge_corpus -v
PYTHONPATH=src python3 -m unittest tests.generated.test_generate_valid_spl -v
python3 tools/generate_valid_spl.py --coverage SPL.txt
PYTHONPATH=src python3 -m spl_frontend
```

The edge corpus currently checks more than 300 distinct source files through
the complete front end, including lexical boundaries, all grammar alternatives,
missing separators and repeated instruction combinations. The generated
coverage program exercises every original grammar production. Seeded programs
have independent limits for expansion count (`max_size`) and concrete-tree node
count (`max_nodes`, default 1000). `SPL.txt` and `tree.xml` are ignored local
artifacts; do not commit them. Executable-only cases still require the packaged
release candidate, and unconfirmed tutor choices remain provisional.

## Phase 1 submission package

Announcement #25 requires one Group 2 ZIP containing a runnable executable
whose filename includes `group-2` and a short PDF manual whose filename also
includes `group-2`. The PDF must list the full names and student numbers of
all four members and explain how tutors run the program. Only the designated
Speaker (`u20598425`) uploads the ZIP to ClickUp before the deadline. The
executable, manual, ZIP and downloaded-copy retest are release artifacts. The
development commands above do not produce them.

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
- Which exact ClickUp upload link will the Speaker use?

The approved GitHub issues link back to the detailed work packets in
`agent_tasks/`.
