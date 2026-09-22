# Shared front-end contracts

Status: **APPROVED on 22 September 2026.**

The common token, token-stream, diagnostic and tree-type foundation is stored
under `src/spl_frontend/`. Owners extend those types without breaking these
contracts.

## Planned package layout

```text
src/spl_frontend/
|-- __init__.py
|-- cli_contract.py
|-- diagnostics.py
|-- source.py
|-- tokens.py
|-- lexer.py
|-- token_stream.py
|-- tree.py
|-- parser.py
|-- xml_writer.py
|-- compiler.py
`-- cli.py

tools/
|-- generate_valid_spl.py
|-- mutate_spl.py
`-- black_box_test.py

tests/
|-- unit/
|-- integration/
|-- generated/
`-- fixtures/
```

## Token contract

```python
@dataclass(frozen=True, slots=True)
class Token:
    token_type: TokenType
    lexeme: str
    line: int
    column: int
    offset: int
```

Rules:

- `lexeme` is the exact consumed token text without its separator.
- Line and column are one-based and point to the first token character.
- Offset is zero-based into the decoded source text.
- EOF is an internal token with an empty lexeme.
- `$` is not an input token.
- `TokenType` contains closed categories for the three lexical classes, every
  keyword, every punctuation token and EOF.

## Lexer contract

```python
def tokenize(source: SourceFile) -> list[Token]:
    """Return all tokens, including exactly one final EOF token."""
```

The lexer raises `LexicalError` for malformed input. It never creates tree
nodes and never makes grammar decisions.

## Token-stream contract

```python
class TokenStream:
    def peek(self, distance: int = 0) -> Token: ...
    def consume(self) -> Token: ...
    def at_end(self) -> bool: ...
```

The parser may use a list-backed implementation. `peek` must not advance.
Tests may build a stream from manually constructed tokens.

## Diagnostic contract

Every expected error contains:

```python
@dataclass(frozen=True, slots=True)
class Diagnostic:
    phase: str
    code: str
    message: str
    path: Path
    line: int
    column: int
    hint: str | None = None
```

Rendered form:

```text
SPL.txt:4:12: syntax[SYN-EXPECTED]: expected ';' but found 'print'
hint: every instruction in ALGO must end with ';'
```

Library modules raise structured project errors. Only the CLI prints them.

## Tree contract

```python
class NodeKind(str, Enum):
    ROOT = "root"
    INNER = "inner"
    LEAF = "leaf"

@dataclass(slots=True)
class TreeNode:
    node_id: int
    kind: NodeKind
    contents: str
    parent_id: int | None
    child_ids: list[int]
```

Required builder operations:

```python
tree.add_root(contents) -> TreeNode
tree.add_inner(contents, parent_id) -> TreeNode
tree.add_leaf(contents, parent_id) -> TreeNode
tree.validate() -> None
```

The tree builder owns deterministic ID assignment and both directions of the
parent/child link. The parser never chooses an ID.

## Parser contract

```python
def parse(tokens: Sequence[Token], tree: SyntaxTree) -> SyntaxTree:
    """Parse the entire token sequence or raise SyntaxError."""
```

The parser creates original-grammar non-terminal nodes and consumed-terminal
leaf nodes. It must finish at internal EOF and must not look at raw characters.

## XML contract

```python
def write_tree(tree: SyntaxTree, output_path: Path) -> None:
    """Validate and atomically replace output_path with deterministic XML."""
```

The XML writer treats the tree as read-only. It writes a temporary sibling
file and replaces `tree.xml` only after successful serialization.

## Compiler and CLI contract

```python
def compile_file(input_path: Path, output_path: Path) -> None: ...
def main(argv: Sequence[str] | None = None) -> int: ...
```

Defaults:

- input: `SPL.txt`
- output: `tree.xml`
- success exit status: `0`
- user/input failure: non-zero
- diagnostics: standard error
- no traceback for expected lexical or syntax errors

The final executable name is provisionally `splc` until submission instructions
say otherwise.

The approved defaults are represented by the shared `CliRequest` value in
`cli_contract.py`. The CLI owner implements argument parsing around that value.
