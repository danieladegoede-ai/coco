# Additive P2 contracts

> Release instruction, 25 October: the Speaker finalized D01-D08 without
> tutor consultation and appointed this AI as main technical reviewer. Use
> [the final release contract](../../release/P2_RELEASE_DECISIONS.md). The dated
> allocations/proposals below are historical and add no consultation or
> named-peer technical-review gate. A33 personal signatures/upload remain real
> personal actions.

Implemented foundation signatures for review under #21/#22, 17 October 2026.
No all-member approval is claimed. P1 approvals/interfaces remain in
[`../01_shared_contracts.md`](../01_shared_contracts.md).

## Driver boundary

`compile_file(input_path: Path, output_path: Path) -> None` remains the P1
frontend coordinator. The default/optional input path, XML schema and exit
statuses are unchanged. #31 will add the full `compile_program` entry point
(or agreed equivalent) and retain a deliberate frontend-only regression API.

Final target: `program.cpp` in the output directory (D01/D08 release contract).
The final driver checks path aliasing before clearing outputs, invalidates
stale target source and publishes atomically only after the required passes
succeed. Keep the existing stale-XML rule until a coordinated change is made.

Current statuses: success 0, usage 2, input 3, lexical 4, syntax 5, tree 6,
internal 70. #31 owns new name/type/generation phases; reserve 7/8/9 only after
that owner records the final choice. Libraries do not print diagnostics.

## Scope, symbol and type records (`semantic_model.py`)

All IDs are positive exact integers (not bool/float aliases). IDs are local
to each SymbolTable/compilation; depth starts at zero.

```python
SemanticType: UNKNOWN, NUMERIC, BOOLEAN, PROCEDURE, OK
NumericMode: INTEGER = "int", FLOAT = "float"
SymbolKind: VARIABLE, PARAMETER, FUNCTION

Scope(scope_id, parent_id, p_node_id, depth)
Symbol(symbol_id, kind, declaration_node_id, scope_id,
       original_name, internal_name,
       value_type=SemanticType.UNKNOWN,
       parameter_ids=(), body_scope_id=None)
```

Scope and Symbol are frozen/slotted dataclasses. Parameter IDs are an ordered
tuple. Functions carry body scope and formal identities; variable/parameter
records cannot carry function signatures. Names allocated by declaration
insertion order look like `spl_v1`, `spl_p2`, `spl_f3`.

```python
table = SymbolTable()
table.add_scope(p_node_id, parent_id=None) -> Scope
table.declare(scope_id, kind, name, declaration_node_id,
              value_type=SemanticType.UNKNOWN) -> Symbol
table.lookup_variable(scope_id, name) -> Symbol | None
table.lookup_function(scope_id, name) -> Symbol | None
table.ancestors(scope_id) -> Iterator[Scope]
table.set_type(symbol_id, value_type) -> Symbol
table.set_function_signature(symbol_id, body_scope_id, parameter_ids) -> Symbol
```

`declare` accepts value_type as keyword-only. `scopes`/`symbols` are read-only
views of builder state. Variable lookup searches current scope then ancestors;
function lookup is direct only. Parameters and locals share duplicate checking.
Separate internal namespaces leave language collision policy D06 undecided.
Bad model inputs raise ValueError; unknown symbol IDs in mutation methods use
KeyError. Analysis passes own translation into phase-specific source diagnostics.
This builder is not the whole name-analysis pass.

## Part 2a name analysis (`name_analysis.py`, #23)

```python
resolve_names(tree: SyntaxTree, source_map: SourceMap | None = None,
              *, path: Path | None = None) -> ResolvedProgram
build_call_hierarchy(program: ResolvedProgram) -> CallHierarchy
```

The name pass validates the graph, collects declarations, then resolves every
name occurrence, including uncalled functions and final return TERM. It never
modifies the tree. Supply aligned original tokens via SourceMap for source
locations; XML-only input uses `path=xml_path` and node IDs. A path supplied
with SourceMap must match its path. No source map defaults to `tree.xml`.

Every P has one scope. Parameters and locals use its shared duplicate domain.
F_TYPE and its keyword/name use the declaring scope; children from the opening
parameter parenthesis through the closing brace use the body scope, with
nested F_TYPE exceptions applied recursively. Branches/loops retain their P.

Symbols start UNKNOWN; arity/types/numeric rules remain #24/#25. Distinct
variable/function spelling domains and body visibility for return TERM are
explicit D06 proposals; no cross-kind spelling rejection is added.

NameAnalysisError(ValueError) fields: code, name, rule, message, hint, node_id,
path, span, related_node_id, related_span. The related fields identify an
earlier duplicate declaration. `render()` uses `name[CODE]` plus real source
positions or a node ID, with a hint. Library code does not print. Malformed
tree/map input uses FoundationError; invalid API argument types use ValueError.

CallHierarchy is a frozen record with a read-only `callees_by_caller` map:
keys are function symbol IDs, with None for main; values are ordered, distinct
callee symbol-ID tuples. Empty entries include uncalled functions. Its
`bottom_up_function_ids` tuple includes all functions, each callee before its
caller, suitable for expanding templates. Individual call sites remain in
the original binding map. The helper rejects cyclic and non-direct bindings
if a downstream consumer constructs an inconsistent replacement snapshot.

See [Part 2a examples and evidence](part_2a_names.md). These are additive
interfaces for review, with no change to the P1 CLI or shared snapshot fields.

## Annotation snapshots

```python
ResolvedProgram(tree, scopes, symbols, scope_by_node,
                binding_by_name_node, source_location_by_node={})
CheckedProgram(resolved, type_by_node, numeric_mode)
```

The implementation uses a default factory, never a shared mutable `{}`.
Constructors copy maps to read-only snapshots. The original P1 tree is not
deep-frozen; consumers must treat its managed nodes as read-only.

ResolvedProgram validates scope ownership/parent depth, complete node scopes,
symbol/declaration references, matching bindings (including declaration leaves),
unique internal names and function signatures. `renamed_name_by_node` is derived
from bindings, preventing a conflicting rename map. It does not run visibility
analysis: #23 must construct correct bindings.

The type owner uses `dataclasses.replace` with typed symbol records to create
a new snapshot. CheckedProgram needs known types on all non-terminals and bound
names, matching symbol types, and an `ok` root. It validates representation
completeness; #24/#25 still enforce production rules and numeric restrictions.

## XML and concrete-tree access

```python
SyntaxTree.from_nodes(nodes: Iterable[TreeNode]) -> SyntaxTree
parse_tree_xml(data: str | bytes, path: Path = Path("tree.xml")) -> SyntaxTree
read_tree(path: str | Path) -> SyntaxTree

iter_preorder(tree, node_id=None) -> Iterator[TreeNode]
iter_postorder(tree, node_id=None) -> Iterator[TreeNode]
iter_leaves(tree, node_id=None) -> Iterator[TreeNode]
iter_list_items(tree, node_id) -> Iterator[TreeNode]
program_parts(tree, node_id) -> ProgramParts
function_parts(tree, node_id) -> FunctionParts
```

Import preserves existing `syntax_tree/root/inner/leaf` tags, IDs, exact
contents and ordered children. Record order need not be creation/ID order.
The public snapshot constructor copies records/child lists, validates and
resumes allocation at the next sequential ID. The reader rejects malformed
XML, document types, invalid scalar IDs, schema ambiguity and invalid graphs.
It validates structure, not full SPL grammar; root-only P1 fixtures are legal.

Validate once at each phase boundary. Traversals are iterative, follow child
edges instead of sorted IDs, and reject repeated/missing references. Lists
flatten V_DECL/F_DECL/INPUT/ALGO only, excluding nullable tails. INPUT yields
top-level TERM items rather than counting nested operands as extra arguments.

ProgramParts fields: variables, functions, algorithm. FunctionParts fields:
return_keyword, name, parameters, body, return_term (None for void). Walkers
validate the local grammar shapes they consume.

## Source mapping and structured errors

```python
SourceSpan(path, line, column, offset, end_line, end_column, end_offset)
build_source_map(tree, tokens: Sequence[Token], path: Path) -> SourceMap
SourceMap(path, source_location_by_node)
SourceMap.span_for(node_id: int) -> SourceSpan | None
```

SourceSpan is frozen. Positions are one-based; offsets zero-based and
end-exclusive. Require exactly one final internal EOF, exact leaf/token
count/lexemes and ordered non-overlapping token positions. Enclosing-node
spans derive from first/last located children; empty productions have no span.
With XML only, use an empty map and node-ID diagnostics. Supply original lexer
tokens before claiming original SPL line numbers.

FoundationError(ValueError) carries code/message and optional path/node_id/span.
`render()` uses path:line:column only for a real supplied span, otherwise
path:node[id] or path alone. XML parser line information stays in the XML error
message, not a fabricated SPL span. Codes: XML-PARSE/XML-TREE/XML-READ,
TREE-* and MAP-*. Modules return/raise silently.

## Downstream backend proposals (not implemented here)

Cherise owns the Instruction/Operand/Label classes (#26), with structural
symbol/label references and per-compilation allocators. Agree these boundaries:

```text
emit_term(term_node_id, destination_operand, expansion_environment)
    -> ordered instructions
emit_instr(instruction_node_id, expansion_environment)
    -> ordered instructions
emit_bool(bool_node_id, true_label, false_label, expansion_environment)
    -> instructions reaching exactly the selected destination
```

Hoist declarations and render at the final boundary. The inliner supplies the
TERM->CALL hook; arithmetic does not implement a second independent inliner.
Explicit two-outcome jumps are the final D03 release choice.

Michele owns FunctionTemplate/ExpansionEnvironment (#29/#30). A template
identifies the resolved function symbol, ordered parameters, body P/IR, locals,
return kind/term/location, and ancestor references. An environment maps symbol
IDs to storage and label IDs to fresh labels, with a parent capture environment.
Preserve root storage; remap locals/formals/returns per call; capture actuals
before populating formals; expand children before parents. D02/D04 are final release choices.

`tests/integration/test_semantic_tree_roundtrip.py` supplies executable fixtures
for four downstream roles without importing nonexistent backend modules or
claiming another member's review/implementation.
