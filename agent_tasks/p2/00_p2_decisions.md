# P2 final decisions - 25 October 2026

The Speaker instructed the group to finish without further tutor consultation
and appointed this AI as the main technical reviewer. D01-D08 are closed
implementation decisions in the [final release contract](../../release/P2_RELEASE_DECISIONS.md).
That contract supersedes the 17/18 October proposals and consultation checklist.
Do not ask the Speaker to obtain tutor answers before proceeding.

## Settled implementation

- D01: C++17 `program.cpp`; preferred g++; explicit gcc C++/libstdc++ fallback.
- D02: cloned formals receive fully evaluated captured actual values.
- D03: explicit true/false comparison/goto transfers; no executable ELSE or
  Boolean composition.
- D04: matching arity for binding, left-to-right complete actual capture,
  short-circuit Booleans. Arity remains a generation policy, not a new 2b rule.
- D05: float for div/decimal NUM, otherwise int; exact global mod/div and
  decimal/mod rejection; standard cout formatting and native representations.
- D06: separate variable/function domains, body-scope returns, nearest-ancestor
  variables and direct-child functions; reject own-parameter masking.
- D07: original `tree.xml`, readable `program.cpp`, internal semantic maps.
- D08: Windows x64, Linux x64 and macOS arm64; documented `group-2` filenames,
  embedded Python runtime, First Class submission and the A33 declarations.

## Evidence and provenance

The source material is the official 2026 Syntax and Parts 2a/2b/3a/3b sheets,
A21/A23/A24/A27/A29/A33 and the supplied A34. A34 explicitly accepts C++ and the
GNU environments; remaining details are final engineering interpretations of
the supplied guidelines, supported by the actual acceptance tests. No tutor
reply or personal member approval is invented.

The [main review](../../release/PR1_MAIN_REVIEW_20261025.md) links all 38 planning
IDs to code and tests. CI reruns the exact native artifacts on all three
platforms. Dated planning packets remain useful ownership history; their old
consultation/approval tasks do not block this authorized technical work.

## A33 completion record

The two declarations are present. Personal signatures and the actual final
First Class upload/receipt are recorded only when supplied or performed. The
build produces an unsigned candidate until then. These personal requirements
are not pending tutor questions and are not satisfied by an AI technical review.
