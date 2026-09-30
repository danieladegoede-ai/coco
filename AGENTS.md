# Instructions for AI coding assistants

## Scope

This repository is for the COS341 SPL front-end assessment only.

The only required pipeline is:

```text
SPL.txt -> source reader -> lexer -> tokens -> parser -> syntax tree -> tree.xml
```

Do not add work outside this front-end pipeline.

## Before changing code

1. Read `README.md`.
2. Read every file in `agent_tasks/` marked as shared.
3. Read the work packet matching the student's number.
4. Check `agent_tasks/00_team_decisions.md`. Do not implement a proposed
   contract that the team has not approved.
5. Inspect the current branch and working tree. Preserve another member's
   changes and do not rewrite files owned by someone else.

## Sources of truth

Use these sources in this order:

1. The official 2026 SPL syntax specification and lecturer announcements.
2. Approved decisions in `agent_tasks/00_team_decisions.md`.
3. Shared interfaces in `agent_tasks/01_shared_contracts.md`.
4. Grammar and lexical reference in `agent_tasks/02_spl_reference.md`.
5. The relevant individual work packet.
6. `README.md`.

If two sources conflict, stop and ask the team Speaker. Never silently invent a
rule.

## Ownership

- `u20598425`: syntax-tree model, XML writer and tree validation.
- `u20620111`: source loading, tokens and lexer.
- `u21434019`: parser and syntax diagnostics.
- `u21448842`: CLI, test generation, black-box testing and executable build.

The exact owned paths and acceptance checks are in the individual work
packets. Do not edit another member's owned paths without that member's
agreement.

## Shared engineering rules

- Support Python 3.11 or later.
- Prefer the Python standard library. Do not add a runtime dependency without
  written team approval.
- Use four spaces, type hints, dataclasses and enums where appropriate.
- Keep source text, tokens and completed tree data deterministic.
- Do not use mutable global state.
- Do not print from library modules; return data or raise a structured error.
- Preserve the original token lexeme and one-based line and column.
- The literal `$` must never be required in `SPL.txt`.
- A failed compilation must not leave a stale or partial `tree.xml`.
- Every implementation change must include relevant tests.
- Do not commit `SPL.txt`, `tree.xml`, caches, virtual environments, build
  output or packaged executables to the source branch.
- Do not create, close or materially change GitHub issues outside the approved
  allocation unless the Speaker requests it.

## Required verification

Once tests exist, run from the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests tools
```

Run the checks relevant to the work packet as well. Report exactly what was
run and any remaining limitations.

## Contract changes

Shared interfaces are deliberately small so the four members can work in
parallel. If a contract must change:

1. Explain why the current contract cannot meet a confirmed requirement.
2. List every owned module affected by the change.
3. Get agreement from those owners before editing.
4. Update `01_shared_contracts.md` in the same pull request.
5. Add or update integration tests.

Do not make an unannounced breaking change merely because it is convenient for
one module.
