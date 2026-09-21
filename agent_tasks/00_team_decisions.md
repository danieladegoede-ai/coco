# Team decisions required before implementation

Status: **PROPOSED - waiting for all four members**

The Speaker records the final choices and changes the status to `APPROVED` only
after all members reply.

## Decision 1: Token representation

### Option A - structured immutable token (recommended)

Fields: token type, original lexeme, one-based line, one-based column and
absolute character offset.

### Option B - tuple

Shorter, but less clear and easier to use incorrectly.

### Option C - type and value only

Simplest, but cannot support accurate error positions.

Proposed choice: **A**

## Decision 2: Token source

### Option A - full token list plus a small token stream (recommended)

The lexer returns all tokens. The parser uses `peek`, `consume` and `at_end`.
Parser tests can provide their own tokens.

### Option B - lexer returns one token at a time

Uses less memory but needs a lookahead buffer and is harder to inspect.

### Option C - parser directly accesses lexer state

Creates tight coupling and blocks independent testing.

Proposed choice: **A**

## Decision 3: Syntax-tree construction

### Option A - shared tree builder (recommended)

The parser calls builder methods. The builder assigns IDs and maintains parent
and child links.

### Option B - nested parser objects with IDs assigned later

Initially simple, but parent references and deterministic IDs are harder later.

### Option C - parser writes XML directly

Couples parsing to output and makes partial-output failures more likely.

Proposed choice: **A**

## Decision 4: Command-line interface

### Option A - no arguments

`./splc` always reads `SPL.txt` and writes `tree.xml`.

### Option B - required input argument

`./splc path/to/input.txt` always requires a path.

### Option C - support both (recommended)

With no argument, read `SPL.txt`. If an argument is provided, read that path.
Write `tree.xml` by default.

Proposed choice: **C**

## Provisional specification decisions

These remain isolated so one tutor answer can change them safely:

- Treat space, CR, LF and CRLF as supported token separators; reject tab.
- Keep the final-token-before-EOF rule configurable until confirmed.
- Represent nullable productions consistently, with the exact XML appearance
  still awaiting confirmation.
- Use a simple internal XML schema until an official sample is supplied.

## Approval record

- [ ] `u20598425`: choices submitted
- [ ] `u20620111`: choices submitted
- [ ] `u21434019`: choices submitted
- [ ] `u21448842`: choices submitted
- [ ] Speaker recorded the accepted choices
- [ ] Status changed to `APPROVED`

Suggested reply format:

```text
1A, 2A, 3A, 4C - agree
```
