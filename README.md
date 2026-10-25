# COS341 SPL Compiler - Group 2

Group 2 earned full marks for P1. Current work targets **P2 1st Class**:
Parts 2a (names/scopes), 2b (types), 3a (algorithm target generation) and 3b
(function inlining), including correct executable target behavior.

The final date is **Sunday 25 October 2026**; the portal closing hour is
unconfirmed. Internal targets aim for a tested native candidate on 23 October
and personally signed, reviewed, verified submission on 24 October.

## Start your AI here

Read [AGENTS.md](AGENTS.md), then [the detailed P2 start guide](agent_tasks/p2/00_START_HERE.md).
The [agent_tasks folder](agent_tasks/README.md) contains a detailed packet and
copyable AI prompt for every member:

| Member | Main issues | Guide |
| --- | --- | --- |
| Rudolph / u20598425 | #21, #22, #23, #36 | [Foundation, names and release](agent_tasks/p2/10_u20598425_foundation_names_release.md) |
| Kuda / u20620111 | #24, #25, #32, #33 | [Numeric policy, types and semantic tests](agent_tasks/p2/20_u20620111_types_numeric_tests.md) |
| Cherise / u21434019 | #26, #27, #28, #34 | [IR, code generation and verification](agent_tasks/p2/30_u21434019_codegen_verification.md) |
| Michele / u21448842 | #29, #30, #31, #35 | [Templates, inlining, driver and native release](agent_tasks/p2/40_u21448842_inlining_driver_release.md) |

[Tracker #20](https://github.com/RudolphLamp/coco/issues/20) holds the live work
allocation. Read [shared interfaces/tutor questions](agent_tasks/p2/05_SHARED_INTERFACES.md)
and [handoff/acceptance](agent_tasks/p2/90_HANDOFF_AND_ACCEPTANCE.md) before editing.

## Current implementation status

The names/types/backend/templates, static inlining and full default compiler
command are integrated. The [driver guide](agent_tasks/p2/part_3b_driver.md)
records APIs, phase statuses and protected output behavior. The final source
acceptance runners and reproducible failure replay commands are described in
[tools/GENERATED_TARGET.md](tools/GENERATED_TARGET.md), with semantic cases and
all 38 original planning IDs linked to executable evidence.

The [24 October source/spec audit](agent_tasks/p2/P2_SPEC_AUDIT_20261024.md)
records the original-sheet/announcement review, parser nesting fix and
500 additional complete-system tests with independently calculated outcomes.
Run them through normal unittest discovery or `python3 tools/run_system_500.py`.

The [25 October expanded audit](agent_tasks/p2/P2_FULL_AUDIT_20261025.md)
adds a 5,000-case edge matrix and ten native numeric-boundary anchors.
`python3 tools/run_edge_5000.py --suite all` runs the retained baseline first,
then the edge matrix with bounded parallel native compilation. Normal unittest
discovery still includes every test; CI uses four disjoint edge shards.

Native packaging and the LaTeX launch manual are now implemented on the release
branch in `danieladegoede-ai/coco`. See [release decisions](release/P2_RELEASE_DECISIONS.md)
and [build/release commands](release/P2_BUILD.md). The workflow creates Windows
x64, Linux x64 and macOS arm64 executables, verifies their exact hashes against
the full packaged corpus, tests GNU 13 target compatibility and assembles a
candidate ZIP. Eight personal signatures and the actual First Class portal
receipt remain personal actions; machine results are not member approvals.

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

For fully valid input, the default command creates `tree.xml` and `program.cpp`.

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

Use the current [P2 packets](agent_tasks/p2/README.md). Each contains owned
paths, full assigned issue requirements, dependencies, concrete expected
results, focused suite names, reviewer and handoff instructions.

The September all-member approval covers the P1 interfaces and allocation.
It is preserved in [the historical decision record](agent_tasks/00_team_decisions.md)
and does not claim approval of new P2 APIs. The old frontend-only packets are
historical references; the current P2 guides supersede their scope/deadlines.

## Basic setup

1. Install Python 3.11 or later.
2. Clone this private repository.
3. Create a short-lived branch for the agreed task.
4. Add the implementation and tests for that task together.
5. Open a pull request and ask another group member to review it.

Do not commit `SPL.txt`, `tree.xml`, Python caches, virtual environments,
packaged executables or private course material.

## Run the compiler during development

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

Successful runs return zero and write fresh `tree.xml` and `program.cpp`
in the current directory. Errors are printed to standard error and return a nonzero status.
The full driver invalidates both outputs before an attempt after protecting
input/output aliases. Phase failures leave no stale successful-looking output. Do not
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
PYTHONPATH=src python3 tools/black_box_test.py
```

For the larger edge corpus and deterministic grammar coverage case:

```sh
PYTHONPATH=src python3 -m unittest tests.integration.test_edge_corpus -v
PYTHONPATH=src python3 -m unittest tests.generated.test_generate_valid_spl -v
python3 tools/generate_valid_spl.py --coverage SPL.txt
PYTHONPATH=src python3 -m spl_frontend --frontend
```

The edge corpus currently checks more than 300 distinct source files through
the complete front end, including lexical boundaries, all grammar alternatives,
missing separators and repeated instruction combinations. The generated
coverage program exercises every original grammar production. Seeded programs
have independent limits for expansion count (`max_size`) and concrete-tree node
count (`max_nodes`, default 1000). `SPL.txt` and `tree.xml` are ignored local
artifacts; do not commit them. Executable-only cases still require the packaged
release candidate, and unconfirmed tutor choices remain provisional.

## Historical Phase 1 submission package

This paragraph records P1 requirements. P2 instead follows #35/#36 and the
[current release gates](agent_tasks/p2/90_HANDOFF_AND_ACCEPTANCE.md), including
two declarations each personally signed by every member.

For P1, Announcement #25 required one Group 2 ZIP containing a runnable executable
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

## Current tutor questions

The [D01-D08 table](agent_tasks/p2/05_SHARED_INTERFACES.md#tutor-decisions)
records unanswered P2 questions: target dialect/toolchain, argument-copy
example, Boolean control-flow invariant, arity/evaluation order, numeric mode/
formatting, namespaces/return visibility, required semantic files, target OS/
launch/signature details and the portal cutoff hour. Keep proposals visibly
provisional until an actual dated answer is recorded.
