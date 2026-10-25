# Part 3b executable inlining (#30)

Builds on the merged #29 template and lexical environment API. Use:

```python
from spl_frontend.inlining import generate_program
from spl_frontend.target_writer import render_target

program = generate_program(checked)
source = render_target(program)
```

`generate_program(CheckedProgram) -> TargetProgram` prepares all immutable
code mines, then supplies `Inliner` as the existing backend's call hook.
`Inliner(checked, *, context=None)` exposes the prepared snapshot and shares
one fresh-name allocator with all executable fragments. A caller can also use
`generate_target(checked, call_emitter=inliner, context=inliner.context)`.
The default CLI is integrated separately by #31.

`TemplateCallEmitter` in call_expansion.py is the shared structural expansion
used both inside parent templates and in executable main. It walks complete
INPUT terms in source order, evaluates each into fresh capture storage, then
copies all captured values into fresh cloned formals. It clones owned
locals/temporaries/returns and labels structurally, remaps ancestor symbols to
the current parent environment, and copies a numeric return into the caller's
destination. Procedures receive no fabricated numeric continuation.

Child/grandchild bodies are already expanded in immutable parent code mines.
An outer clone therefore remaps both the parent's slots and child references
to them. Root SymbolRefs retain shared global identity. No runtime SPL calls,
stack, string-based renaming or nested main definitions are emitted. The safe,
inactive code-mine view precedes the executable skeleton as shown in Part 3b.

TERM planning uses the existing backend work stack, so nested actual calls do
not add recursive generation frames. Template and executable instruction
budgets each guard runaway static growth. Expected failures are silent
`CodegenError` values with code/message/node and optional real source span/path;
`render()` never invents source positions for XML-only callers.

D02 uses formal = captured actual. D04 uses matching arity, left-to-right
capture and short-circuit Booleans. These are isolated, documented backend
proposals; Part 2b does not acquire a new arity rule. D01-D08 remain pending.
Native int/float ranges and precision apply; no new overflow/definite-assignment
rejection or tutor answer is invented.

## Verification

```sh
PYTHONPATH=src python3 -m unittest tests.unit.test_inlining \
  tests.integration.test_codegen_calls tests.unit.test_function_templates \
  tests.integration.test_function_templates -q
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 -m compileall -q src tests tools
PYTHONPATH=src python3 tools/black_box_test.py
git diff --check
```

Execution tests compile/run actual C++ with timeouts and handwritten expected
outputs. They cover zero/one/multiple complete arguments, nonzero formal copies,
left-to-right side effects and early captures, calls in all numeric contexts,
short circuit and reevaluated loop conditions, repeated parent/child captures,
grandparent/global writes, shadowing, loop-label freshness, 180 nested actual
calls, deterministic immutable templates and consistently typed float returns.
No native compiler package is built by this issue. PR results record actual
local platform/toolchain and counts; no unrun hosted/member approval is claimed.
