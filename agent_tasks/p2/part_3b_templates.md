# Part 3b template and environment handoff (#29)

This focused change builds on the foundation/name work merged through #37/#38,
semantic analysis in #41 and structural backend in #40. It implements reusable
function templates and lexical environments. Executable main-call integration
belongs to #30, and the full public compiler driver belongs to #31.

Executable call expansion is now available through the
[#30 inlining API](part_3b_inlining.md). The preparation API below remains
compatible; #31 separately integrates the default compiler command.

## Public API

```python
from dataclasses import replace
from spl_frontend.codegen import CodegenContext, generate_target
from spl_frontend.function_templates import prepare_function_templates
from spl_frontend.target_writer import render_target

context = CodegenContext(checked)
prepared = prepare_function_templates(checked, context=context)
# A program without main-level calls can display the inactive code mine now.
program = generate_target(checked, context=context)
source = render_target(replace(program, code_mine=prepared.code_mine))
```

`prepare_function_templates(CheckedProgram, *, context=None)` returns an
immutable `PreparedFunctionTemplates` with:

- `checked`: the original checked semantic snapshot;
- `templates`: a read-only mapping from resolved function symbol ID to
  `FunctionTemplate`;
- `preparation_order`: function IDs, with every lexical child before its parent,
  including uncalled declarations;
- `code_mine`: safe `CodeMineSection` values for the existing target writer.

A `FunctionTemplate` records symbol/body scope/P IDs, ordered formals, locals,
children, captured ancestor IDs, return kind and optional return TERM/storage,
owned structural declarations/instructions/labels, and symbol-to-storage maps.
Tuple fields and copied read-only maps preserve reusable definitions.

Formals and locals use `StorageRef` identities. Free ancestor variables remain
`SymbolRef` identities until their current parent instance is known. Child
calls expand inside the parent template during preparation; cloning that parent
then remaps its owned slots, including the child references to those slots.
A later parent instance therefore cannot write into an earlier instance.
The original syntax tree, source spellings, bindings and checked snapshot stay
intact. No template contains a main definition or executable runtime SPL call.

## Cloning contract for #30

Use the shared `CodegenContext`/allocator throughout preparation and expansion.
Create a fresh mapping for every slot in `template.declarations`, then call:

```python
clone_fragment(
    IRFragment(template.declarations, template.instructions),
    context.allocator,
    storage_remap=fresh_owned_storage,
    symbol_remap=current_environment,
)
```

The existing IR clone operation remaps storage, definitions and goto targets
structurally. It preserves literal/comment text. Use the same explicit mapping
for the ordered formal locations and optional return storage. Ancestor symbol
remaps must point to the current instantiated ancestor; globals can retain
root `SymbolRef` identities. Call-site actual capture, formal population and
caller continuation publication are the separate #30 integration boundary.

`ExpansionEnvironment(scope_id, storage_by_symbol={}, parent=None)` is an
immutable `Mapping[int, StorageLocation]`. `resolve(symbol_id)` walks only the
current environment and its parents, by declaration ID; missing storage and
parent cycles produce structured `CodegenError`. It accepts `StorageRef` and
`SymbolRef`, copies incoming maps, and distinguishes separate parent instances.
The `parent` relation is lexical, never a sibling search.

## Invariants and policies

Preparation rechecks the call hierarchy and rejects forged recursive/invisible
bindings deliberately. Records validate return metadata, owned storage and
labels. A one-million-instruction limit guards static template growth.
Library functions do not print or publish files. Code-mine serialization uses
the existing safe line-comment writer, including nested instruction comments
and backslash handling.

Inside template preparation, D02 uses formal = captured actual. D04 uses exact
arity, left-to-right complete TERM capture and short-circuit Booleans. These
are final backend choices; they are not new Part 2b type rules. D01-D08 are
settled in the release contract and require no consultation.

## Evidence

Run with Python >=3.11:

```sh
PYTHONPATH=src python3 -m unittest tests.unit.test_function_templates \
  tests.unit.test_expansion_environment tests.integration.test_function_templates -q
PYTHONPATH=src python3 -m unittest tests.unit.test_name_analysis \
  tests.integration.test_name_analysis_pipeline -q
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 -m compileall -q src tests tools
PYTHONPATH=src python3 tools/black_box_test.py
git diff --check
```

The template integration tests compile and execute real C++ using explicit
consumer fixtures. They establish inactive templates, safe annotations,
`5:9:90` for two cloned parent/child captures with a distinct global, and `23`
for two loop clones with disjoint storage/labels. They do not install the #30
inliner or #31 driver. Names tests cover the existing N01-N10 implementation.
The PR records actual counts and toolchain; local checks do not certify hosted
Windows/Linux execution or a native package. Native builds and admin work are
outside this issue. No another-member approval or signature is claimed.
