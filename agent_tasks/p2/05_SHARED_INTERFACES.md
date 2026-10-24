# Shared P2 interfaces and decisions

Updated 18 October 2026. Read this before one module chooses representations
that another owner must consume. The official 2026 sheets and actual tutor
answers take precedence. An implemented API can still await team review.

## Current template handoff (24 October)

The implemented #29 API and structural clone/capture contract are documented
in [Part 3b templates](part_3b_templates.md). It consumes the actual checked
model and backend from merged #37/#38/#41/#40. The 18 October snapshots below
remain historical interface records. Main-call inlining and full CLI
integration are separate #30/#31 tasks.

## Inlining and full command implementation

The [inlining API](part_3b_inlining.md) and
[full compiler/CLI guide](part_3b_driver.md) record the actual #30/#31
implementation on this branch. P1 status codes remain and name/type/generation
add 7/8/9. Source generation runs all passes; `--frontend` explicitly preserves
syntax-only regression use. D01-D08 below remain pending.

## Availability and authoritative implementation

On this documentation refresh, main contains P1 implementation. Foundation
code is in [#37](https://github.com/RudolphLamp/coco/pull/37); names are in
[#38](https://github.com/RudolphLamp/coco/pull/38). Do not assume a module exists
on main because its signature appears here. Inspect/fetch the appropriate
branch; after merge, inspect main. Never add a duplicate semantic model merely
to bypass a pending dependency.

Implemented source/contracts for comparison:

- [Foundation contract at a8703f5](https://github.com/RudolphLamp/coco/blob/a8703f5088b38922c0e5b85ff4ad2872d74ca672/agent_tasks/p2/01_p2_contracts.md)
- [Name-pass contract at 1853a64](https://github.com/RudolphLamp/coco/blob/1853a64cf69847d89909211b6d73d4b187ff4c87/agent_tasks/p2/01_p2_contracts.md)
- [Name-pass usage and N01-N10 evidence](https://github.com/RudolphLamp/coco/blob/1853a64cf69847d89909211b6d73d4b187ff4c87/agent_tasks/p2/part_2a_names.md)

These immutable links are the original handoff snapshots. Read live revisions
and reviews before implementation; they do not record all-member approval.

## Preserve existing P1 boundaries

```python
tokenize(source: SourceFile) -> list[Token]
parse(tokens, tree: SyntaxTree, path: Path = DEFAULT_INPUT_PATH) -> SyntaxTree
write_tree(tree: SyntaxTree, output_path: Path) -> None
compile_file(input_path: Path, output_path: Path) -> None
main(argv=None) -> int
```

The current compile_file is frontend-only. SourceFile carries path/text;
Token is immutable and retains token_type, lexeme, one-based line/column and
zero-based offset. Exactly one final internal EOF is present; it is not an
SPL input token or XML leaf. See the approved P1 files in ../ for full details.
The as-built lexer raises FrontendError; parse has the optional path shown
above. Do not implement against outdated illustrative exception names.

Current statuses: success 0, usage 2, input 3, lexical 4, syntax 5, tree 6,
internal 70. Michele owns the coordinated P2 phases/status additions in #31;
7/8/9 are proposals, not already-reserved public behavior. Preserve actual
input paths and traceback-free expected errors.

## Foundation records implemented in #22

All IDs are positive exact integers, excluding bool/float aliases, and are
local to one compilation. Scope depth begins at zero.

```python
SemanticType: UNKNOWN, NUMERIC, BOOLEAN, PROCEDURE, OK
NumericMode: INTEGER = "int", FLOAT = "float"
SymbolKind: VARIABLE, PARAMETER, FUNCTION

Scope(scope_id, parent_id, p_node_id, depth)
Symbol(symbol_id, kind, declaration_node_id, scope_id,
       original_name, internal_name, value_type=SemanticType.UNKNOWN,
       parameter_ids=(), body_scope_id=None)

ResolvedProgram(tree, scopes, symbols, scope_by_node,
                binding_by_name_node, source_location_by_node={})
CheckedProgram(resolved, type_by_node, numeric_mode)
```

The displayed empty map is illustrative; implementation uses a default factory.
Records/maps are immutable snapshots; treat the original tree's managed nodes
as read-only. renamed_name_by_node is derived from each name's symbol binding.
Every P has one scope and every tree node a scope annotation. Every name leaf,
including declarations, has a binding. A function has its child body scope and
ordered formal IDs. Symbols use deterministic internal names such as spl_v1,
spl_p2 and spl_f3. Distinct declarations never share internal names.

SymbolTable is a builder, not the whole semantic pass. Its methods are:

```python
add_scope(p_node_id, parent_id=None) -> Scope
declare(scope_id, kind, name, declaration_node_id, *, value_type=UNKNOWN) -> Symbol
lookup_variable(scope_id, name) -> Symbol | None
lookup_function(scope_id, name) -> Symbol | None
ancestors(scope_id) -> Iterator[Scope]
set_type(symbol_id, value_type) -> Symbol
set_function_signature(symbol_id, body_scope_id, parameter_ids) -> Symbol
```

Parameter/local duplicates share one domain; functions use a separate direct
table. This representation does not invent a cross-kind language restriction.
The type pass can use dataclasses.replace to produce typed Symbol records and
a new ResolvedProgram. Keep the original resolved result unchanged. A
CheckedProgram needs known types on all non-leaf nodes and bound name leaves,
types matching typed symbols, an OK root and one NumericMode. Punctuation does
not need fabricated numeric types. Its constructor validates completeness,
not production correctness: #24/#25 still perform the actual checks.

## Tree access and original source positions

Implemented in #22:

```python
SyntaxTree.from_nodes(nodes) -> SyntaxTree
parse_tree_xml(data: str | bytes, path=Path("tree.xml")) -> SyntaxTree
read_tree(path) -> SyntaxTree
iter_preorder(tree, node_id=None)
iter_postorder(tree, node_id=None)
iter_leaves(tree, node_id=None)
iter_list_items(tree, node_id)
program_parts(tree, node_id) -> ProgramParts
function_parts(tree, node_id) -> FunctionParts
build_source_map(tree, tokens, path: Path) -> SourceMap
```

Use child-edge traversal order, not sorted node IDs or XML record order.
iter_list_items supports V_DECL/F_DECL/INPUT/ALGO; INPUT yields complete TERM
arguments, not each nested operand. ProgramParts has variables/functions/
algorithm. FunctionParts has return_keyword/name/parameters/body/return_term;
return_term is None for void. Nullable nodes have no consumed token.

The XML reader validates schema/graph and preserves IDs, contents and ordered
links. It is not a second grammar parser. SourceMap aligns original tokens to
leaves exactly and derives enclosing spans; span_for(node_id) can return None.
SourceSpan contains path, line, column, offset, end_line, end_column, end_offset.
Positions are one-based; offsets zero-based and end-exclusive. XML-only input
has node IDs, not invented SPL source lines. FoundationError carries code,
message, path/node/span and render(); libraries do not print it.

## Name results implemented in #23

```python
resolve_names(tree, source_map=None, *, path=None) -> ResolvedProgram
build_call_hierarchy(resolved) -> CallHierarchy
```

Use path=xml_path without tokens. A path supplied alongside SourceMap must
agree. The name pass collects declarations before uses, checks uncalled bodies,
and retains UNKNOWN symbol types for #25. Names are never mutated in the tree.
F_TYPE/its keyword/name are in the declaring scope; its parameter/body/return
tail uses the child scope. Branches/loops remain in their containing P scope.

NameAnalysisError(ValueError) carries code, name, rule, message, hint, node_id,
path, span, related_node_id and related_span. Duplicate errors identify the
previous declaration. Its render() uses name[CODE] and actual positions or
node IDs. The driver must handle this error deliberately, not as internal 70.

CallHierarchy.callees_by_caller is read-only: None means main; function symbol
IDs identify other callers/callees; tuple values deduplicate ordered edges.
bottom_up_function_ids includes all functions with actual callees before
callers. Uncalled declarations still have entries. Call-site bindings stay
in the resolved map. Defensive cycle/visibility checks protect replacement
snapshots; they do not introduce legal recursion.

## Backend interfaces to agree before integration

These are proposals for Cherise/Michele/Kuda to settle in focused PR review,
not implemented imports promised by main. Keep the final public model small.

- #24 returns immutable whole-program numeric facts plus one selected mode.
  #25 combines those facts with production checking into CheckedProgram.
  The driver invokes each policy once through its agreed coordinator.
- #26 supplies Instruction/Operand/Label and structural symbol references,
  deterministic per-compilation allocators, clone/remap and target validation.
  One rendered program owns all declarations and exactly one main.
- #27/#28 accept checked symbols, a destination/environment and the inliner's
  call hook. The intended boundaries are:

  ```text
  emit_term(term_node_id, destination_operand, expansion_environment)
  emit_instr(instruction_node_id, expansion_environment)
  emit_bool(bool_node_id, true_label, false_label, expansion_environment)
  emit_call(call_node_id, destination_or_none, expansion_environment)
  ```

- #29 supplies FunctionTemplate keyed by function symbol ID, with ordered
  formals, owned locals, return kind/TERM, body IR/labels and captured ancestor
  symbols. ExpansionEnvironment maps declaration IDs to this call's storage,
  remaps labels and follows the current instantiated parent environment.
- #30 captures actuals before populating formals, clones fresh storage/labels,
  expands nested calls and writes numeric returns into the caller's result
  destination. Root/shared storage and captured writes retain their identity.
- #31 owns compile_program or the final equivalent, library-to-CLI errors,
  target filename and atomic lifecycle. A separate frontend-only API preserves
  syntax regressions. Generation of source does not inherently require a
  target compiler installed; automatic target compilation is a separate choice.

All generated temporaries/captures/returns use the same selected numeric mode.
Declare storage before goto-controlled statements; initialized declarations
must not make gotos invalid C++. Define every label once, with a legal following
statement, and resolve every jump. Avoid text replacement in identifiers,
strings or comments. Code-mine content remains safely non-executable.

## Tutor decisions

Unanswered at the documentation refresh. Record actual date, answer/source,
affected owners/tests and resulting implementation change after consultation.
Do not replace an unanswered row with an inferred approval.

| ID | Question and isolated current proposal | Responsible members |
| --- | --- | --- |
| D01 | Sheets say C but show iostream/cout. Propose C++ and program.cpp; confirm dialect, filename and compile/run commands. | Speaker, Cherise, Michele |
| D02 | Part 3b's pN=aN copy appears reversed. Propose cloned formal = captured actual; demonstrate a nonzero argument. | Speaker, Michele |
| D03 | Confirm emit_bool(B,T,F) explicit true/false transfers with comparison/goto lowering; demonstrate nested not/or. | Speaker, Cherise |
| D04 | Confirm arity and evaluation order. Propose matching counts, left-to-right actual capture and short-circuit Booleans. | Speaker, Kuda, Michele |
| D05 | Propose int with mod; float with div or decimals; otherwise int. Confirm output formatting. Only the explicit global conflicts reject. | Speaker, Kuda |
| D06 | Confirm variable/function same spelling and return-TERM visibility. Keep separate namespaces and body-scope returns without invented restrictions. | Speaker, Rudolph |
| D07 | Are renamed tree/type/symbol-table files required, with what schema? Keep inspectable maps without inventing output-file requirements. | Speaker |
| D08 | Confirm tutor OS/CPU, commands, extra files, Linux artifact, group filenames, signature method and portal closing hour. | Speaker, Michele |

Confirmed numeric restrictions do not wait for D05: both mod/div anywhere must
reject with the exact required message, and mod forbids any decimal NUM.
Confirmed names do not wait for D06: nearest-ancestor variables, no sideways
lookup, own-parameter masking and immediate-F_DECL calls remain mandatory.
