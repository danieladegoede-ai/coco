# SPL front-end reference

This is an implementation checklist derived from the supplied 2026 syntax
specification and Announcement 23. When wording is uncertain, consult the
official document and ask the tutor.

## Lexical rules

Every token must be followed by the specification's `blank_space`. The
underscore shown at the end of lexical regular expressions represents that
separator; it is not a literal underscore in `SPL.txt`.

### NUM

Required forms include:

- `0`
- a non-zero unsigned or negative integer with no leading zero
- an unsigned or negative decimal whose last fractional digit is `1` to `9`

Important negative cases include `-0`, leading-zero integers, a decimal with no
fractional digit, and a decimal ending in zero. Use ASCII `-` in source text.

### USER-DEFINED-NAME

- Begins with `#`.
- Remaining characters are lowercase ASCII letters or digits.
- The supplied regular expression technically allows no characters after `#`;
  keep this case covered and confirm it if needed.
- Uppercase letters, underscore and punctuation are invalid.

### STRING

- Begins and ends with `"`.
- Interior characters come only from the listed lowercase letters, digits and
  punctuation: comma, full stop, colon, hyphen, question mark and exclamation.
- Test empty strings, allowed punctuation, missing closing quote, uppercase
  letters, spaces and unsupported characters.

### Keywords

```text
void num return print nop comment if then else
while until do not and or eq larger lesser
mod add sub mul div neg
```

### Punctuation

```text
( ) { } : ; =
```

`$` is not punctuation in the source language. It is only an EOF meta-symbol.

## Complete grammar

```text
SPL_PROG -> P EOF
P        -> V_DECL : F_DECL : ALGO

V_DECL   -> epsilon
V_DECL   -> USER-DEFINED-NAME V_DECL

F_DECL   -> epsilon
F_DECL   -> F_TYPE F_DECL

F_TYPE   -> void USER-DEFINED-NAME ( V_DECL ) { P return }
F_TYPE   -> num USER-DEFINED-NAME ( V_DECL ) { P return ( TERM ) }

ALGO     -> epsilon
ALGO     -> INSTR ; ALGO

OUTP     -> ( TERM )
OUTP     -> STRING

INSTR    -> print OUTP
INSTR    -> nop
INSTR    -> comment STRING
INSTR    -> ASSIGN
INSTR    -> BRANCH
INSTR    -> LOOP
INSTR    -> CALL

CALL     -> USER-DEFINED-NAME ( INPUT )

INPUT    -> epsilon
INPUT    -> TERM INPUT

ASSIGN   -> USER-DEFINED-NAME = TERM

TERM     -> USER-DEFINED-NAME
TERM     -> NUM
TERM     -> CALL
TERM     -> mod ( TERM TERM )
TERM     -> add ( TERM TERM )
TERM     -> sub ( TERM TERM )
TERM     -> mul ( TERM TERM )
TERM     -> div ( TERM TERM )
TERM     -> neg ( TERM )

BRANCH   -> if BOOL then { ALGO } else { ALGO }

BOOL     -> not ( BOOL )
BOOL     -> and ( BOOL BOOL )
BOOL     -> or ( BOOL BOOL )
BOOL     -> eq ( TERM TERM )
BOOL     -> larger ( TERM TERM )
BOOL     -> lesser ( TERM TERM )

LOOP     -> COND BOOL do { ALGO }
LOOP     -> do { ALGO } COND BOOL

COND     -> while
COND     -> until
```

## Predictive parsing notes

The raw grammar has two user-name prefix conflicts:

1. In `INSTR`, assignment and call both start with a user-defined name. Inspect
   the next token: `=` selects assignment and `(` selects call.
2. In `TERM`, a plain name and call both start with a user-defined name. `(`
   selects call; otherwise parse a name term.

Implement the decision without speculative parsing or parse-and-rewind. Keep
helper factoring out of the output tree so it still represents the supplied
grammar.

## Required tree properties

- Exactly one root representing `SPL_PROG`.
- A unique integer ID for every root, inner and leaf node.
- Original grammar non-terminals as inner-node contents.
- Consumed token lexemes as leaf contents.
- Ordered immediate child IDs on root and inner nodes.
- One valid parent ID on every non-root node.
- No cycles, duplicate IDs, dangling references or unreachable nodes.
- Deterministic XML for identical input.

## Announcement 23 testing rules

- Generate valid programs forward from `SPL_PROG`.
- Bound recursion and size so generation always finishes.
- Every generated valid program must parse without an error.
- Make invalid cases by changing one known part of a valid program.
- Check that the error location and message make sense.
- Never insert `$` into generated source.
- Test the final executable as a black box; tutors will not rebuild it.
