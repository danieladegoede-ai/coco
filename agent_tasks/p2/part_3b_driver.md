# Complete compiler command and output safety (#31)

This branch depends on the #30 inlining PR. The public command now performs
source loading, lexing/parsing and tree validation, source mapping, names,
whole-tree numeric/types, static inlining, closed-IR validation and target
serialization before publishing successful results.

```sh
PYTHONPATH=src python3 -m spl_frontend
PYTHONPATH=src python3 -m spl_frontend "path/to/input with spaces.spl"
```

Use Python >=3.11. Default input is `SPL.txt`; `tree.xml` and `program.cpp` go
in the current working directory. Every source token, including the final one,
needs its supported separator. Original tree IDs/spellings remain in XML;
semantic renames and types stay in immutable side maps.

Generation requires Python, not an installed target compiler. The compiler
writes source and does not automatically compile or execute it. Actual target
execution tests explicitly invoke C++ with timeouts. C++/program.cpp is D01's
recorded proposal; no tutor approval or native platform result is invented.

## Public library boundaries

```python
compile_file(input_path, output_path) -> None  # P1 syntax/XML compatibility
compile_tree(tree, source_map=None, *, path=None) -> CompilationResult
compile_program(input_path, target_path=Path("program.cpp"),
                *, xml_path=Path("tree.xml")) -> CompilationResult
```

`CompilationResult` contains `checked` and `target_source`. `compile_tree`
publishes nothing. With source tokens, pass `build_source_map(...)` for real
spans. For imported XML, use `compile_tree(read_tree(xml), path=xml)`; semantic
and generation errors then retain that filename and node ID without fabricated
source lines. XML and in-memory runs produce equivalent checked/generated data.

The explicit syntax-only command is:

```sh
PYTHONPATH=src python3 -m spl_frontend --frontend path/to/input.spl
```

It uses the preserved `compile_file` API and manages only XML. This mode is for
P1 grammar fixtures that may have invalid names/types; it does not manage the
P2 target file. Existing syntax-generator CLI tests retain their assertions and
now select this mode explicitly. The default assessment command runs all passes.

## Status and diagnostics

| Status | Meaning |
| --- | --- |
| 0 | Requested pipeline succeeded |
| 2 | Usage error |
| 3 | Input/read/path/alias error |
| 4 | Lexical error |
| 5 | Syntax error |
| 6 | Tree/XML/foundation error |
| 7 | Name error |
| 8 | Numeric/type error |
| 9 | Generation/backend policy/target publication error |
| 70 | Unexpected internal failure or failure to clear previous output |

Libraries raise silent structured errors. Only the CLI prints diagnostics to
stderr. Expected failures have no traceback. Backend errors render as
`codegen[CODE]`; target-write errors use `generation[GEN-WRITE]`. Source paths
reach the parser and semantic phases; output write errors identify the output.

## Output lifecycle

Alias checks happen before any deletion: input cannot be either output, and
XML/target cannot alias one another. Resolved paths, symlinks and existing hard
links are accounted for. Alias rejection preserves all affected files.

After preflight, both old outputs are invalidated before source loading. All
required passes must succeed before fresh XML or target is published. A lexical,
syntax, name, type, generation or read failure therefore leaves neither output
looking current. XML is published only for a fully successful checked program.

Each file is written through a temporary sibling and atomic replacement. If
publication fails, this attempt's XML/target are removed and temporary target
state is cleaned up, preserving the actionable error. Publication is atomic per
file, not a two-file transaction across process termination or power loss.
Cleanup failures are reported where the OS prevents removing prior outputs.

## Verification

```sh
PYTHONPATH=src python3 -m unittest tests.integration.test_full_compiler \
  tests.test_cli tests.integration.test_pipeline -q
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 -m compileall -q src tests tools
PYTHONPATH=src python3 tools/black_box_test.py
git diff --check
```

The default command runs in an actual subprocess and its arithmetic and
nested/repeated-call targets compile and execute with expected `2.5` and `5:9`.
Tests also cover valid-error-valid sequences across all semantic phases,
missing/unreadable/non-ASCII inputs, input/output alias protection, hardlinked
outputs, denied publication after XML succeeds, temporary cleanup, XML-only
filename/node diagnostics, round-trip equivalence and the curated semantic
source corpus. Local results/toolchain are recorded in the PR. Hosted checks,
native packaging (#35), release administration (#36) and overall #33/#34
acceptance sign-off remain separate. D01-D08 stay provisional.
