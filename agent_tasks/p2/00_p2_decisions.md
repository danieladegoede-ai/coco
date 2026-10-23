# P2 decisions and consultation record

17 October 2026. Sources: official 2026 Syntax and Parts 2a/2b/3a/3b sheets;
Announcements 21, 23, 24, 28, 29 and 33. Course PDFs stay private.

## Authorization and review

The Speaker requested the allocation and implementation of #21/#22, then #23
on the foundation branch. New interfaces are additive review proposals.
P1 approvals of 22 September remain
recorded separately and do not imply approval of these P2 additions.

- [ ] Kuda21 reviewed model/type annotation contracts.
- [ ] CheriseHeyl reviewed tree walking and target-interface proposals.
- [ ] michey-n reviewed XML/source maps and template/driver boundaries.
- [ ] Speaker recorded actual shared-interface review outcomes.

PR reviews supply that evidence. No breaking P1 interface change is needed;
the only P1 code addition is the public `SyntaxTree.from_nodes` constructor.

## Confirmed requirements

- P2 1st Class includes 2a, 2b, 3a, 3b and executable target code, for up to
  6/6 P2 points. The group reports P1 full marks.
- Final date is Sunday 25 October; A33 gives no closing hour.
- The manual has category and final-ZIP approval declarations, each personally
  signed by every member. Upload only to the 1st Class slot.
- Variables use nearest current/ancestor lookup, never sideways siblings (A21).
  A local cannot mask its own parameter.
- A P algorithm calls only functions in its immediate F_DECL. No overloading
  or direct/indirect recursion. Function lookup differs from variable lookup.
- Same entity gets one internal name; different entities get different names.
  Tree node IDs link semantic records without destroying original lexemes.
- Both mod and div anywhere require the exact Part 2b conflict message.
  Any mod forbids decimal NUM anywhere, including uncalled bodies.
- Boolean composition and ELSE become comparison/goto control flow. All four
  loop forms and function inlining are required.

## Implementation choices for review

Use deterministic per-compilation Scope/Symbol IDs. Variables and parameters
share a lookup domain; functions use a direct table. Separate internal tables
do not decide whether cross-kind spelling collisions are legal.

Store annotations in read-only node-ID mapping snapshots. Retain P1 tree
contents/IDs. Validate XML before returning a tree; align original tokens with
source-order leaves. Empty productions and XML-only input have no invented SPL
line numbers. The frontend command and exit codes remain unchanged until #31.

The #23 pass uses body scope for the final numeric return TERM, and separate
variable/function spelling domains without an extra collision error. These
remain D06 proposals, not tutor answers. Scope annotations put F_TYPE/name in
the declaring P and its parameter/body/return tail in the child body scope.
The pass adds no arity, definite-assignment or type rule. A derived call
hierarchy checks cycles and direct-child edges before the inliner consumes it.

## Tuesday 20 October consultation

| ID | Question / current proposal | Owner / status |
| --- | --- | --- |
| D01 | Sheets say C but use iostream/cout. Propose C++ `program.cpp`; confirm dialect, filename and target compile/run command. | Speaker; unanswered |
| D02 | Part 3b captures actual in pN then prints pN=aN. Propose cloned formal = captured actual; show nonzero argument. | Speaker/michey-n; unanswered |
| D03 | Confirm explicit emit_bool(B,T,F) true/false transfers with no executable ELSE/composition; show nested-not/or example. | Speaker/CheriseHeyl; unanswered |
| D04 | Confirm arity and evaluation order. Propose matching formal/actual counts, left-to-right capture and short-circuit Booleans. | Speaker/Kuda21/michey-n; unanswered |
| D05 | Propose int with mod; float with div or decimals; otherwise int. Only explicit global conflicts reject. Confirm output formatting. | Speaker/Kuda21; unanswered |
| D06 | Confirm variable/function same spelling and return-TERM body visibility; keep internal symbol kinds separate. | Speaker; unanswered |
| D07 | Are renamed tree/types/symbol-table files required, and in what schema? Keep annotations inspectable without inventing a file requirement. | Speaker; unanswered |
| D08 | Confirm tutor OS/CPU, launch command, extra files/Linux binary, group-number naming, signature method if prescribed and portal cutoff. | Speaker; unanswered |

Record the actual answer, date, source and affected tests. A passing fixture
or implementation proposal is not a tutor answer. Consultation follow-up stays
in #20/#36 while the additive foundation is prepared now for review.
