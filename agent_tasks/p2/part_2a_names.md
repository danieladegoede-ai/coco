# Part 2a: names, scopes and renaming (#23)

Original owner: RudolphLamp / u20598425. The name pass is integrated; the
Speaker's final release contract settles D06 without further consultation.
Sources reviewed: private 2026 Part 2a pp.1-4 and Announcement 21. The N IDs
below are the planning requirement IDs, not extra lecturer requirements.

## Public entry point

```python
from pathlib import Path
from spl_frontend.lexer import tokenize
from spl_frontend.name_analysis import resolve_names, build_call_hierarchy
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.source_map import build_source_map
from spl_frontend.tree import SyntaxTree

path = Path("example.spl")
source = "#x : num #f ( #a ) { : : return ( #a ) } : #x = #f ( 1 ) ; "
tokens = tokenize(SourceFile(path, source))
tree = parse(tokens, SyntaxTree(), path)
resolved = resolve_names(tree, build_source_map(tree, tokens, path))
hierarchy = build_call_hierarchy(resolved)
```

That example has scopes 1 (main) and 2 (#f body), and symbols:

| Symbol ID | Original | Kind | Scope | Internal |
| --- | --- | --- | --- | --- |
| 1 | #x | variable | 1 | spl_v1 |
| 2 | #f | function | 1 | spl_f2 |
| 3 | #a | parameter | 2 | spl_p3 |

The function has body_scope_id=2 and parameter_ids=(3,). Main's call edge is
None -> 2; bottom_up_function_ids=(2,). Symbols retain UNKNOWN type until the
type pass. A declaration and all its uses select the same symbol/internal name.

`resolved.scope_by_node`, `binding_by_name_node`, `renamed_name_by_node`,
`scopes`, `symbols` and `source_location_by_node` are read-only snapshots.
Read the original tree as immutable: no original name, ID, child link or XML
byte is changed by name analysis. Internal names use declaration identity,
never a global search-and-replace by spelling.

For XML-only input, use `resolve_names(read_tree(xml_path), path=xml_path)`.
No SPL source line is inferred from XML record order or XML line numbers.

## Resolution and policies

1. Validate the graph and the local declaration/name-bearing shapes consumed
   by this pass. The imported tree must still represent parser output; the
   name pass is not a second full grammar validator.
2. Collect parameters, locals and direct function declarations before uses.
   Locals cannot duplicate each other or that body's own parameters. Nested
   child declarations can shadow an ancestor. Branches/loops add no scopes.
3. Resolve variables through current scope then nearest parent, never across
   siblings/cousins. Each sibling has a separate identity even at equal depth.
4. Resolve calls in the caller P's direct function table only. Self, siblings,
   ancestors, undeclared names and deeper descendants are invisible. A child
   with the same spelling as its parent is a separate entity and can be called
   by that parent. Two separate parents may each declare their own #helper.
5. Check every declared body, including uncalled ones. Derive actual call
   edges and a deterministic callee-before-caller order for the inliner.
   Cycles and non-direct bindings in replacement snapshots are rejected too.

Declaration allocation is deterministic: for each P, parameters in written
order, then locals, then all direct functions; visit child P bodies in written
depth-first order. The root scope is first; direct child scopes are allocated
in declaration order before their bodies are processed. All traversal follows
child links rather than numeric node/record ordering. No global allocator is
shared across compilations. The traversal and cycle check are iterative.

D06 is final for this release: variable/function spellings use separate tables with
no invented cross-kind collision error; numeric return TERM sees body locals,
parameters, ancestors and direct child functions. Those tests document the
final release behavior. No arity, type or definite-assignment rule is added
by the name pass. See the final release contract for its test evidence.

## Diagnostics

Catch NameAnalysisError and call error.render(). Fields identify the original
name, failed rule, hint and node; a real SourceMap adds source path/line/column.
Duplicate errors also identify the earlier declaration and its span if known.
Without tokens, the renderer uses xml_path:node[id]. No library output occurs.

| Code | Trigger |
| --- | --- |
| NAME-DUPLICATE-VARIABLE | Duplicate local/global in one V_DECL |
| NAME-DUPLICATE-PARAMETER | Duplicate formal in one parameter list |
| NAME-PARAMETER-MASK | Body local duplicates its own formal |
| NAME-DUPLICATE-FUNCTION | Same-name declarations in one F_DECL, regardless of signature/type |
| NAME-UNDECLARED-VARIABLE | No variable/formal in the current/ancestor chain |
| NAME-INVISIBLE-FUNCTION | No function in the immediate caller F_DECL |
| NAME-RECURSION | Protective call-cycle check on replacement snapshots |

The minimal `: void #f ( #x ) { #x : : return } : ` fails with
NAME-PARAMETER-MASK even when main never calls #f. Ordinary recursion attempts
fail NAME-INVISIBLE-FUNCTION first, before a cyclic graph can be constructed.

The public command still writes P1 tree.xml until #31 integrates the semantic
passes and agrees CLI statuses. A P1 syntax fixture can therefore pass the
frontend yet fail the separately invoked name pass, as intended.

## Requirement evidence

| Rule | Focused evidence in test_name_analysis / test_name_analysis_pipeline |
| --- | --- |
| N01 | Complete scope annotations, branch/all-loop P environment, 1,100 nested scopes |
| N02 | Current/outer/global lookup and exact nearest binding identities |
| N03 | Independent sibling locals, third-sibling rejection, A21 cousin rejection/fallback to global |
| N04 | Separate duplicate-local and duplicate-parameter rejections |
| N05 | Minimal own-parameter masking rejection; legal deeper local/formal shadowing |
| N06 | Direct calls; self/sibling/ancestor/deep-descendant failures; return calls |
| N07 | Duplicate functions including differing formals/return types; separate-parent helpers |
| N08 | Self/mutual call rejection; injected self/indirect cycle guards |
| N09 | Same entity identity, distinct shadow names, repeat/XML/renumbered-tree stability |
| N10 | Silent success/failure; structured errors with exact repeated-token positions or XML nodes |

The ten fixtures under tests/fixtures/semantics/names have an expected-result
manifest and are parsed by the real frontend before checking semantic results.
The integration suite exercises actual resolved results in explicit type-model
and inliner fixtures; it does not claim those later passes are implemented or
that another member has reviewed the interface.

## Verification and review

Use Python 3.11 or later. Commands from the repository root:

```sh
PYTHONPATH=src python3 -m unittest tests.unit.test_name_analysis tests.integration.test_name_analysis_pipeline -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests tools
PYTHONPATH=src python3 tools/black_box_test.py
```

Local verification: 43 focused tests and 363 full-suite tests passed on macOS
arm64, /opt/homebrew/bin/python3 3.14.0. compileall passed; the CLI black-box
runner passed 10/10 cases. Exact commands replace python3 above with
/opt/homebrew/bin/python3. The PR link is recorded in #23 and tracker #20.
CI must run Windows/Linux on Python 3.11;
the existing zero-job Actions startup failure is not evidence of a hosted pass.
Review by Kuda21, merge of the foundation and name PRs, and any actual member
demonstration are separate pending gates. No approval or tutor answer is implied.
