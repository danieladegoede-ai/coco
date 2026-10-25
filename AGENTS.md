# Instructions for Group 2 coding assistants

## Current scope: P2, 1st Class

P1 earned full marks. Current authorized work is COS341 2026 Parts 2a, 2b,
3a and 3b: names/scopes, types, target generation and function inlining.
The goal is the 1st Class assessment, up to 6/6 P2 points. The final date is
Sunday 25 October 2026; the portal closing hour is still unconfirmed.

Start with **[agent_tasks/p2/00_START_HERE.md](agent_tasks/p2/00_START_HERE.md)**.
It selects the correct personal packet, explains branches/dependencies and
lists the shared rules. These P2 instructions supersede the old frontend-only
scope and September allocation in the historical P1 packets. Preserve those
modules and their regression coverage.

The intended pipeline is:

```text
SPL.txt -> existing lexer/parser -> validated syntax tree
        -> names/scopes/renaming -> numeric/type checks
        -> target IR + function templates/inlining -> validated target source
```

Documentation on main does not mean all these passes are merged. Check the
live branch, source files, issues and PRs before importing an API. Foundation,
names, numeric/types, backend and templates are merged through #37/#38/#41/#40/#42.
The full driver and inlining are integrated. Source acceptance uses the
semantic/target runners in tools/GENERATED_TARGET.md. Preserve the original
38 requirement IDs and E01-E10 meanings when updating cases. Read the
[current command/API guide](agent_tasks/p2/part_3b_driver.md); the dated personal
packets below remain historical task allocations.

## Required reading before editing

1. Root README and the P2 start guide.
2. Your student-number packet and its current GitHub issues.
3. [Shared interfaces](agent_tasks/p2/05_SHARED_INTERFACES.md), including
   implemented-versus-proposed API status and pending tutor decisions.
4. [Handoff and acceptance](agent_tasks/p2/90_HANDOFF_AND_ACCEPTANCE.md).
5. The official private 2026 sheets/announcements relevant to your issue,
   the P1 shared contracts and grammar reference under agent_tasks.
6. Existing code/tests and git status on the actual branch you will edit.

Resolve links relative to the packet location. Do not assume a private Desktop
path, another person's checkout or a missing PDF exists on a teammate's machine.
The packet includes local task detail. If a necessary course source is
unavailable, use the recorded confirmed rules, isolate uncertain policy and
report the missing evidence precisely.

## Authorized native release work (25 October)

The Speaker explicitly authorized #35/#36 implementation on
`danieladegoede-ai/coco`, synchronizing the tested P2 source from
`RudolphLamp/coco`. Read `release/P2_RELEASE_DECISIONS.md`: supplied A34 resolves
the C++ designation and GNU toolchain preference. Use the native build/test
workflow and LaTeX manual. This supersedes earlier exclusion of packaging/manual
work. Personal approvals/signatures and actual portal submission must remain
truthful; do not tick or sign for members without their own consent/signatures.

## Ownership

| Member | Current issues | Detailed packet |
| --- | --- | --- |
| RudolphLamp / u20598425 | #21, #22, #23, #36 | [Foundation, names, release](agent_tasks/p2/10_u20598425_foundation_names_release.md) |
| Kuda21 / u20620111 | #24, #25, #32, #33 | [Numeric policy, types, semantic tests](agent_tasks/p2/20_u20620111_types_numeric_tests.md) |
| CheriseHeyl / u21434019 | #26, #27, #28, #34 | [IR, code generation, verification](agent_tasks/p2/30_u21434019_codegen_verification.md) |
| michey-n / u21448842 | #29, #30, #31, #35 | [Templates, inlining, driver, native release](agent_tasks/p2/40_u21448842_inlining_driver_release.md) |

Issue/path ownership replaces the old P1 blanket ownership of whole test
directories. Each issue owns its named tests; multiple members may add
different tests under tests/integration. Preserve another member's edits.
P1 source owners remain Rudolph (tree/XML), Kuda (source/tokens/lexer),
Cherise (parser), Michele (CLI/driver/build). Coordinate changes to their
existing modules. Do not implement another owner's issue to hide a dependency.

## Working rules

- The user's assigned implementation request authorizes routine work in that
  issue's owned paths, tests and documentation. Proceed to a concrete PR;
  do not repeatedly ask whether to begin. Review requirements apply at merge.
- Support Python 3.11 or later, use standard-library dependencies where
  practical, four spaces and type hints. No global compilation state.
- Preserve original lexemes, source positions, tree IDs, ordered child links
  and the P1 XML contract. Semantic results are side maps, not in-place renames.
- Distinguish nearest-ancestor variable lookup from direct-child function
  lookup. Respect the exact numeric conflict rules. Add no unsupported
  grammar, type, arity or definite-assignment restriction.
- Use resolved symbol IDs and structural IR references. Avoid raw-text
  identifier/label replacement. Implement required inlining; no runtime SPL
  call stack or alternate parser.
- Libraries return results or structured errors; only CLI code prints errors.
  Report real input locations, or node IDs for XML without original tokens.
- Check input/output aliasing before deletion. Failed compiles must not leave
  misleading stale or partial outputs. Coordinate any XML lifecycle change.
- Keep tutor-dependent decisions visibly provisional. Do not invent a tutor
  answer, team approval, signature, test pass, clean-machine result or upload.
- Keep private course material, inputs/outputs, caches, environments, binaries
  and ZIPs out of source commits. Use temporary/ignored output directories.
- Keep changes focused, add meaningful regression tests and report actual
  commands/results. An interface fixture is not an implemented downstream pass.

## Verification and handoff

Run focused tests and the applicable full suite from the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests tools
PYTHONPATH=src python3 tools/black_box_test.py
git diff --check
```

Use Python >=3.11; the default python3 on a machine may be older. For backend
work also compile and execute the generated target with timeouts and independent
expected outputs. See the shared handoff file for native/package gates.

An issue is ready for integration only after its real dependencies, tests and
review criteria are satisfied. A formal block permits independent fixtures and
explicitly stacked development; it does not permit claiming full completion.
Open a focused PR, link the issue/parent PR, name the reviewer, and give paths,
commit, exact checks/results, provisional decisions and remaining gates.

## Contract changes and precedence

Official 2026 sheets/announcements take precedence over generic compiler
examples. Actual dated tutor answers take precedence over a recorded proposal.
The September all-member approval covers P1 interfaces, not new P2 approvals.
For a breaking shared-interface change, explain the confirmed requirement,
identify affected owners, obtain their agreement, update the shared contract
and integration tests together. Additive implementations may be prepared for
review within the assigned issue; do not silently redefine another module's API.
