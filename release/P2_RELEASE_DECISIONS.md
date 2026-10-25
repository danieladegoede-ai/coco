# Final P2 release contract - 25 October 2026

The Speaker instructed that this release be completed without further tutor
consultation and designated this AI as the main technical reviewer. **D01-D08
are closed release decisions.** Apply the choices below; dated planning packets
and audits do not reopen them. Official 2026 requirements remain the source of
truth. These are implemented decisions supported by tests, with A34 supplying
the target-language clarification; no new tutor reply is claimed.

| ID | Final decision | Requirement basis and execution evidence |
| --- | --- | --- |
| D01 | Emit readable C++17 in `program.cpp`; prefer `g++ -std=c++17`. Also support `gcc -x c++ -std=c++17 program.cpp -lstdc++ -o program`. | Supplied A34 accepts the C++ designation and GNU compiler environments. The GNU 13 job executes all 31 target cases through each driver. C++17 is the selected compatible dialect, not a claimed exact version required by A34. |
| D02 | Evaluate actuals into fresh captures, then assign **cloned formal = captured actual**. | Part 3b requires the callee to receive its input values. Its displayed inverse assignment would overwrite the captures and lose those values. Nonzero/multiple-input cases C01-C04 demonstrate the implemented transfer and side effects. |
| D03 | Use explicit true/false destinations with comparisons, labels and gotos. Emit no executable ELSE or Boolean composition. | Part 3a requires jump-based branching. B06/B07 and C13 check nested not/or/and, false paths and short circuiting. Exact temporary names or branch-block layout are not treated as a textual template. |
| D04 | Require matching actual/formal counts for executable binding. Evaluate complete actual terms left to right before formal copies. Evaluate Booleans with short circuiting. | Part 3b counts ordered INPUT terms and binds them to the function parameters. C02-C04 and C13 check capture order/side effects. Arity failure is a generation diagnostic (status 9), not an invented Part 2b type error. |
| D05 | Use one numeric mode for the whole program: float if div or decimal NUM occurs; otherwise int. Reject both mod/div with the exact specified message, and reject mod with any decimal NUM. Use native int32/binary32 on the release targets and standard cout formatting. | Part 2b gives the two global conflicts; 3a/3b require one int/float target type. B02/B03, C15 and NB01-NB10 check division, remainder, representation and output. Strings do not select numeric mode. No additional lexical range restriction is added. |
| D06 | Keep variable/function naming domains separate; resolve return TERM in its function body's scope. Parameters and body locals share a duplicate domain. Variables use nearest ancestors; calls use only the current P's direct F_DECL. | Parts 2a/2b and A21 define the scope restrictions without requiring a cross-kind collision rule. E01/E02/E03, E10 and C05-C07 check shadowing, forbidden sideways lookup, own-parameter masking and current ancestor captures. |
| D07 | Publish the original `tree.xml` plus readable `program.cpp`. Preserve tree IDs/lexemes; keep binding, rename, scope and type maps internally for subsequent passes. | Syntax requires original node data/links; Parts 2a/2b use the symbol table for consistent identities/types. The supplied sources give no additional public symbol-table file schema. XML round-trip tests compare original records and generated target bytes. |
| D08 | Ship Windows x64 `group-2.exe`, Linux x64 `group-2`, and supplemental macOS arm64 `macos/group-2`. The embedded Python runtime needs no separate Python installation. A separate C++ compiler runs generated targets. Use the documented commands and final `group-2.zip` naming. | The user authorized all three native builds; A33 requires an assessment executable and launch PDF, and A34 requires the target-toolchain details. Native/package/extracted-ZIP jobs test these exact platform paths. Unix executables have no extension. No tutor-machine confirmation is needed to build or document this supported set. |

## Final interpretation boundaries

The implementation choices above settle the previously recorded questions.
They require no consultation or additional policy approval. The main review
traces all 38 original planning IDs to code/tests in
[PR1_MAIN_REVIEW_20261025.md](PR1_MAIN_REVIEW_20261025.md). Native integer range,
single-precision float rounding and the documented 1,000,000-instruction static
expansion limit remain implementation characteristics, not new syntax rules.

## Personal submission actions required by A33

These are personal actions, not unresolved compiler decisions:

- Each of the four members personally signs both declarations after reviewing
  the exact release. The manual provides eight signature/date rows.
- Incorporate those signed pages into the final PDF; verify the final ZIP's
  contents, execution and checksum, then use `group-2.zip` for submission.
- The Speaker submits only in the First Class slot on 25 October before the
  cutoff displayed in that slot, retains its receipt and verifies the downloaded
  copy. No arbitrary closing hour is assumed.

Until those acts occur, CI correctly labels its output `group-2-candidate.zip`
and records zero supplied signatures and `submission_ready: false`. Those
facts must not be turned into fictitious signatures or a fictitious receipt.
