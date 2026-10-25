# Main technical review of worker PR #1 - 25 October 2026

PR: https://github.com/danieladegoede-ai/coco/pull/1

Reviewed starting head: `96464479146864ab3d82e8f96245ae2082c4aed7`.
Review fixes: `b0573d0` (exact PDF/native/GNU evidence binding).
The compiler under `src/` remains identical to the audited upstream P2 source
`c2fb92c3c78764322a4c42db84a8941fe12fe51e`; this review did not replace a pass
or change language semantics. Both repository histories remain present.

## Verdict and scope

The implemented names/scopes, types, algorithm generation and static inlining
cover the supplied 2026 Parts 2a/2b/3a/3b and all 38 internal planning IDs below.
No additional compiler behavior defect was found in this review. Two release
evidence gaps were reproduced and fixed; additional native/black-box checks
now strengthen the same assembly boundary. The changed release code requires
fresh hosted checks before its new candidate can replace the prior one.

**The assignment is not yet a completed submission.** The provided A33 still
requires eight genuine personal signatures, final signed-archive verification
and one real First Class upload. Neither this AI review nor CI supplies those
personal acts. A mark of 6/6 is an assessment outcome, not a claim made here.

This is the technical review requested by the Speaker. It does not claim to
be Cherise's, Kuda's or Michele's personal approval, or an independent human
review. GitHub's formal request to Cherise was rejected with HTTP 422 because
she is not a collaborator of the worker repository. No repository permission
or review protection has been bypassed.

## Findings, in order of release impact

### R1 - OPEN: the candidate is unsigned; A33 submission is incomplete

Source: A33, supplied announcement text, and local `assoument13.txt`.
The two declaration texts are present in [the LaTeX source](group-2.tex#L124),
but all four signature rows on each remain blank. That is intentional and
truthful. The [assembler](../tools/assemble_release.py#L69) records zero personal
signatures and `submission_ready: false`; it produces `group-2-candidate.zip`.

Required completion: each member personally signs both declarations after
reviewing this release; incorporate those pages, verify the exact final PDF
and ZIP, name the submission `group-2.zip`, upload only in the First Class
slot, retain the receipt and compare the downloaded archive's SHA-256.
The exact portal closing hour and tutor computer's OS/CPU were not provided;
the manual states the tested platforms rather than inventing confirmations.
These personal/external items remain in original-repository #35/#36.

### R2 - FIXED: a replaced PDF could pass assembly

Before this review, `validate_artifacts` checked the manual's recorded source
commit and page count, but did not bind that record to `group-2.pdf`. A local
reproduction replaced the PDF with arbitrary bytes while retaining its
metadata; the old validator still accepted the artifacts. A passing layout
job therefore did not guarantee that assembly shipped the PDF it checked.

Fix: [the manual builder](../tools/build_manual.py#L37) records PDF SHA-256 and
size after text/layout checks; [assembly](../tools/assemble_release.py#L53)
requires that exact existing PDF. Regression tests reject replaced, missing,
unbound and wrong-size manuals. This changes verification, not the declaration
contents or any person's consent.

### R3 - FIXED: GNU acceptance did not identify the tested Linux binary

The GNU reports previously contained case results and commands, but no binary
hash. Assembly could not establish that those results certified the Linux
executable included in the ZIP. The original fixture accepted this missing
provenance, independently of the 31 passed case IDs.

Fix: [the GNU runner](../ci/test_gcc13.py#L8) records the Linux executable's hash,
checks that it remains unchanged through both driver runs, and records the
actual driver version strings. [Assembly](../tools/assemble_release.py#L50)
compares both reports to the shipped Linux hash. Tests reject stale/unbound
reports and a binary changed during validation. Fresh Linux/GNU hosted
execution is required; old results are not relabelled as new evidence.

### R4 - FIXED: assembly trusted native identity and black-box metadata too broadly

The build job already inspected native file magic and CPU. Assembly now
independently rechecks the received PE/ELF/Mach-O identity, expected CPU,
filename and byte size, alongside its hash and acceptance identity. It also
explicitly requires the successful black-box result. Tests include a PE CPU
changed to x86 with all associated hashes updated: the format check still
rejects it, rather than trusting a Windows x64 label.

All these regression tests live in
[the release gate suite](../tests/unit/test_release_tools.py). It now has
33 methods, including 13 new rejection tests. The positive fixture uses real
native header structures so format validation is exercised.

## Source material and interpretation

The 19 private inputs in [the source fingerprint record](../agent_tasks/p2/P2_SPEC_SOURCE_FINGERPRINTS.json)
were checked against the local originals and still match byte for byte.
No private sheet, scan or rendered page is committed by this review.

| Source | Reviewed requirement and consequence |
| --- | --- |
| Syntax pp. 1-3 | Exact lexical forms and separators, recursive grammar, internal EOF only; original token spellings and unique XML node links. P1 behavior remains covered. |
| Part 2a pp. 1-4 | Nearest current/ancestor variables; distinct scope identity; no duplicate locals/formals or own-parameter masking; direct-child functions only; no overload/recursion; consistent declaration-based internal names and diagnostics. All four scanned pages were visually rechecked. |
| A21 | A same-depth sibling or cousin declaration is not an ancestor. Tests must distinguish sideways lookup from legitimate global/ancestor access. |
| Part 2b pp. 1-4 | Complete traversal including unused bodies/returns; numeric/procedure contexts; nullable/list/control/output attributes; exact global mod/div error and decimal/mod rejection. All four coloured pages were visually rechecked. |
| Part 3a pp. 1-7 | Readable typed target, ordered terms/output, arithmetic, primitive comparison/goto control flow, no executable ELSE or Boolean composition, all four loop forms. All seven coloured pages were visually rechecked. |
| Part 3b pp. 1-3 | Inactive function code mine, capture all actual values, static copy/expansion, numeric continuation, child-before-parent preparation and fresh labels for every copy. All three coloured pages were visually rechecked. |
| A23 | Valid and intentionally faulty inputs, real executable assessment and internal EOF notation. Source-only passes are not packaged-executable evidence. |
| A24/A27/A29 | First Class comprises 2a, 2b, 3a and 3b, including executable generated targets; the P1 mark does not establish P2 correctness. |
| A33 | Personally signed category and whole-ZIP declarations; one First Class upload; executable and launch manual in the group archive. Eight signature rows are not eight signatures. |
| A34, supplied in this thread | C++ designation is accepted; target remains human-readable and inspectable; document preferred compiler and check GNU g++/gcc compatibility. GNU 13 family is tested; no exact uninstalled 13.0.0 version is claimed. |

The sheets call their translations guidelines/hints rather than a required
byte-for-byte listing. The implementation retains primitive comparisons and
gotos while using explicit true/false transfers and a different branch-label
layout. Declaration hoisting prevents illegal gotos across initialized C++
variables. Inactive templates use safe C++ line comments; no runtime SPL
function declarations/calls or stack replace inlining. These are the reviewer's
implementation judgments, not invented tutor statements about exact syntax.

The ambiguous actual/formal assignment direction is implemented as cloned
formal = captured actual; reversing it would lose the supplied value. Matching
arity, left-to-right actual evaluation, short circuiting, separate variable/
function namespaces, body-scope returns, native int/float representation and
`tree.xml`/`program.cpp` output policy remain explicitly documented choices in
[P2_RELEASE_DECISIONS.md](P2_RELEASE_DECISIONS.md). This review does not convert
those choices into dated tutor confirmations.

## Complete requirement trace

These are the original **38 planning IDs**, not an official marking rubric.
All referenced test methods were checked to exist. The full case-level links
remain in [requirements.json](../tests/fixtures/codegen/requirements.json),
[74 semantic cases](../tests/fixtures/semantics/cases.json),
[31 target cases](../tests/fixtures/codegen/acceptance/cases.json) and the
[E01-E10 anchors](../tests/fixtures/codegen/acceptance/planning_anchors.json).
PASS below means implemented with the recorded tests; it does not mean all
possible SPL programs or external submission actions have been proved.

| ID | Requirement | Implementation inspected | Concrete test evidence | Result |
| --- | --- | --- | --- | --- |
| N01 | Create a scope hierarchy by nested P/function bodies. Track scope identity as well as depth. | [add_scope](../src/spl_frontend/semantic_model.py#L183) | [test_empty_program_has_one_scope_and_complete_annotations](../tests/unit/test_name_analysis.py#L61)<br>[test_sibling_locals_with_same_spelling_are_distinct](../tests/unit/test_name_analysis.py#L95) | PASS |
| N02 | A variable use must resolve in its current scope or an ancestor; choose the nearest matching declaration. | [lookup_variable](../src/spl_frontend/semantic_model.py#L237) | [test_current_outer_global_and_nearest_shadowing](../tests/unit/test_name_analysis.py#L78) | PASS |
| N03 | Never search sideways into sibling functions or their descendants. [A21] | [lookup_variable](../src/spl_frontend/semantic_model.py#L237) | [test_announcement_21_cousin_uses_ancestor_not_sideways_declaration](../tests/unit/test_name_analysis.py#L115) | PASS |
| N04 | Reject duplicate variable names in one declaration scope, including duplicate parameters. | [declare](../src/spl_frontend/name_analysis.py#L95) | [test_duplicate_locals_and_parameters_and_parameter_masking](../tests/unit/test_name_analysis.py#L140) | PASS |
| N05 | A function body local may not mask a parameter of that same function. | [declare](../src/spl_frontend/name_analysis.py#L95) | [test_child_local_and_parameter_may_shadow_ancestor_parameter](../tests/unit/test_name_analysis.py#L128)<br>[test_duplicate_locals_and_parameters_and_parameter_masking](../tests/unit/test_name_analysis.py#L140) | PASS |
| N06 | Calls from a P algorithm may target only functions declared in the immediate F_DECL of that P. | [bind_use](../src/spl_frontend/name_analysis.py#L184) | [test_undeclared_self_sibling_mutual_ancestor_and_deep_calls_fail](../tests/unit/test_name_analysis.py#L197) | PASS |
| N07 | Function names in the applicable F_DECL must be unique; no overloading. | [declare](../src/spl_frontend/name_analysis.py#L95) | [test_duplicate_functions_reject_overloading_by_parameters_or_return_type](../tests/unit/test_name_analysis.py#L155) | PASS |
| N08 | No direct or indirect recursion. Strict child-only visibility is the primary rule. | [build_call_hierarchy](../src/spl_frontend/name_analysis.py#L260) | [test_guard_rejects_indirect_cycle_in_modified_binding_snapshot](../tests/unit/test_name_analysis.py#L437) | PASS |
| N09 | Consistently rename every declaration and use: same entity, same internal name; different entities, different internal names. | [declare](../src/spl_frontend/semantic_model.py#L205) | [test_record_and_node_number_order_do_not_control_binding](../tests/integration/test_name_analysis_pipeline.py#L91) | PASS |
| N10 | Reject rule violations with appropriate messages; accept compliant programs without name errors. | [fail](../src/spl_frontend/name_analysis.py#L84) | [test_source_diagnostic_points_to_the_specific_repeated_occurrence](../tests/unit/test_name_analysis.py#L301)<br>[test_all_semantic_manifest_cases_through_final_cli](../tests/integration/test_full_compiler.py#L266) | PASS |
| T01 | Attributes and symbols | [_seed_declarations](../src/spl_frontend/type_analysis.py#L108) | [test_check_is_repeatable_and_does_not_mutate_resolved_tree_or_symbols](../tests/unit/test_type_analysis.py#L295) | PASS |
| T02 | Variables and functions | [_check_f_type](../src/spl_frontend/type_analysis.py#L238) | [test_variable_type_is_numeric](../tests/unit/test_type_analysis.py#L272)<br>[test_void_function_type_is_procedure](../tests/unit/test_type_analysis.py#L279)<br>[test_num_function_type_is_numeric](../tests/unit/test_type_analysis.py#L286) | PASS |
| T03 | Calls and INPUT | [_check_call](../src/spl_frontend/type_analysis.py#L379) | [test_function_with_multiple_parameters](../tests/unit/test_type_analysis.py#L182)<br>[test_multiple_whole_term_actuals](../tests/integration/test_codegen_calls.py#L58) | PASS |
| T04 | Call context | [_check_instr](../src/spl_frontend/type_analysis.py#L290) | [test_num_function_as_instruction_fails](../tests/unit/test_type_analysis.py#L191)<br>[test_void_function_in_term_fails](../tests/unit/test_type_analysis.py#L197) | PASS |
| T05 | Assignment / leaves | [_check_assign](../src/spl_frontend/type_analysis.py#L353) | [test_simple_assignment](../tests/unit/test_type_analysis.py#L36) | PASS |
| T06 | Arithmetic | [scan_numeric_policy](../src/spl_frontend/numeric_policy.py#L54) | [test_nested_arithmetic](../tests/unit/test_type_analysis.py#L95)<br>[test_mod_and_div_conflict_exact_message](../tests/unit/test_numeric_policy.py#L78)<br>[test_mod_with_decimal_conflict](../tests/unit/test_numeric_policy.py#L89) | PASS |
| T07 | Booleans / control | [_check_bool](../src/spl_frontend/type_analysis.py#L556) | [test_and](../tests/unit/test_type_analysis.py#L124)<br>[test_do_until_loop](../tests/unit/test_type_analysis.py#L153)<br>[test_and_or_truth_tables_not_and_all_comparisons](../tests/integration/test_codegen_control_flow.py#L88) | PASS |
| T08 | Output / simple instructions | [_check_outp](../src/spl_frontend/type_analysis.py#L335) | [test_print_numeric](../tests/unit/test_type_analysis.py#L46)<br>[test_print_string](../tests/unit/test_type_analysis.py#L41)<br>[test_nop_instruction](../tests/unit/test_type_analysis.py#L51)<br>[test_comment_instruction](../tests/unit/test_type_analysis.py#L56) | PASS |
| T09 | Structural productions | [_check_p](../src/spl_frontend/type_analysis.py#L193) | [test_empty_program](../tests/unit/test_type_analysis.py#L29)<br>[test_void_function_as_instruction](../tests/unit/test_type_analysis.py#L162) | PASS |
| T10 | Complete traversal | [_check_tree](../src/spl_frontend/type_analysis.py#L127) | [test_uncalled_function_numeric_conflict_detected](../tests/unit/test_type_analysis.py#L234)<br>[test_all_semantic_manifest_cases_through_final_cli](../tests/integration/test_full_compiler.py#L266) | PASS |
| G01 | Preserve ALGO instruction order; empty ALGO terminates cleanly. Emit readable statements and newlines. | [emit_algorithm](../src/spl_frontend/codegen.py#L268) | [test_minimal_program_is_valid_and_has_exactly_one_main_and_return](../tests/unit/test_target_writer.py#L38)<br>[test_issue_arithmetic_anchor_matrix](../tests/integration/test_codegen_arithmetic.py#L27) | PASS |
| G02 | print STRING writes the string; print(TERM) computes into a temporary and writes its value. | [emit_instr](../src/spl_frontend/codegen.py#L193) | [test_all_hand_computed_backend_anchors_compile_and_execute](../tests/integration/test_executable_semantics.py#L64) | PASS |
| G03 | nop becomes a harmless comment; comment STRING becomes a target comment. | [_render_instruction](../src/spl_frontend/target_writer.py#L156) | [test_comments_do_not_interfere_with_executable_output](../tests/integration/test_codegen_arithmetic.py#L46) | PASS |
| G04 | Assignment computes the TERM first, then stores it in the renamed target variable. | [emit_term](../src/spl_frontend/codegen.py#L137) | [test_issue_arithmetic_anchor_matrix](../tests/integration/test_codegen_arithmetic.py#L27) | PASS |
| G05 | NAME and NUM terms copy into a result location. Operators map to %, /, +, -, *, and unary -. | [emit_term](../src/spl_frontend/codegen.py#L137) | [test_issue_arithmetic_anchor_matrix](../tests/integration/test_codegen_arithmetic.py#L27)<br>[test_division_of_integer_looking_literals_is_fractional](../tests/unit/test_codegen_terms.py#L34) | PASS |
| G06 | Every generated variable has the selected whole-program int or float type. | [render](../src/spl_frontend/target_writer.py#L84) | [test_float_arguments_locals_and_returns_use_one_selected_mode](../tests/integration/test_codegen_calls.py#L162) | PASS |
| G07 | Translate branches using labels and goto; no executable ELSE command. | [_emit_control](../src/spl_frontend/codegen.py#L281) | [test_nested_branch_inside_loop_preserves_control_flow](../tests/integration/test_codegen_control_flow.py#L154) | PASS |
| G08 | Lower Boolean composition into jumps, not target and/or/not or &&////! expressions. | [emit_bool](../src/spl_frontend/boolean_codegen.py#L61) | [test_and_or_truth_tables_not_and_all_comparisons](../tests/integration/test_codegen_control_flow.py#L88)<br>[test_hand_checked_precision_remainder_and_short_circuit_anchors](../tests/generated/test_compiled_semantics.py#L28) | PASS |
| G09 | Support pre-test while, pre-test until, post-test while and post-test until. | [_emit_control](../src/spl_frontend/codegen.py#L281) | [test_all_four_loop_forms_zero_one_and_repeated_iterations](../tests/integration/test_codegen_control_flow.py#L129) | PASS |
| G10 | Use resolved internal names, fresh temporaries and unique labels throughout. | [FreshNameAllocator](../src/spl_frontend/codegen_ir.py#L513) | [test_repeated_loop_function_has_fresh_jump_targets](../tests/integration/test_codegen_calls.py#L105)<br>[test_seeded_complete_programs_match_model_oracle_and_full_cli](../tests/generated/test_compiled_semantics.py#L21) | PASS |
| F01 | Emit one root main, the needed declarations and return 0. Nested P bodies supply templates, not nested main definitions. | [render](../src/spl_frontend/target_writer.py#L84) | [test_minimal_program_is_valid_and_has_exactly_one_main_and_return](../tests/unit/test_target_writer.py#L38)<br>[test_grandchild_updates_current_grandparent_and_global](../tests/integration/test_codegen_calls.py#L95) | PASS |
| F02 | Build reusable, non-executable templates keyed by resolved function symbol. Retain the code-mine concept in the generated output. | [_prepare_templates](../src/spl_frontend/function_templates.py#L100) | [test_uncalled_function_code_mine_produces_no_output_or_state_change](../tests/integration/test_codegen_calls.py#L132)<br>[test_mine_annotations_are_comment_safe_and_target_still_compiles](../tests/integration/test_codegen_calls.py#L138) | PASS |
| F03 | Walk the recursive INPUT chain to count ordered TERM arguments. | [plan_call](../src/spl_frontend/call_expansion.py#L51) | [test_zero_and_one_argument_return_nonzero_value_copy](../tests/integration/test_codegen_calls.py#L46)<br>[test_multiple_whole_term_actuals](../tests/integration/test_codegen_calls.py#L58) | PASS |
| F04 | Evaluate actual arguments into fresh capture temporaries before populating the cloned formal parameters. | [plan_call](../src/spl_frontend/call_expansion.py#L51) | [test_all_actuals_are_captured_before_later_argument_side_effects](../tests/integration/test_codegen_calls.py#L64)<br>[test_actuals_evaluate_left_to_right](../tests/integration/test_codegen_calls.py#L72) | PASS |
| F05 | Inline void bodies for instruction calls; inline num bodies and copy the return result into the caller continuation variable. | [plan_call](../src/spl_frontend/call_expansion.py#L51) | [test_calls_in_assignment_print_arithmetic_comparison_actual_and_return](../tests/integration/test_codegen_calls.py#L114)<br>[test_void_procedure_returns_no_numeric_value_and_preserves_root_write](../tests/integration/test_codegen_calls.py#L125) | PASS |
| F06 | Expand a child function inside its parent template before the parent is inserted into main. | [_prepare_templates](../src/spl_frontend/function_templates.py#L100) | [test_grandchild_updates_current_grandparent_and_global](../tests/integration/test_codegen_calls.py#L95) | PASS |
| F07 | Each expansion has unique labels, temporaries, local/formal storage and return storage. | [clone_fragment](../src/spl_frontend/codegen_ir.py#L598) | [test_repeated_loop_function_has_fresh_jump_targets](../tests/integration/test_codegen_calls.py#L105)<br>[test_repeated_compilations_are_deterministic_and_independent](../tests/integration/test_codegen_calls.py#L155) | PASS |
| F08 | Captured ancestor variables retain the correct binding under expansion. | [resolve](../src/spl_frontend/expansion_environment.py#L32) | [test_child_updates_current_parent_local_on_each_call](../tests/integration/test_codegen_calls.py#L80)<br>[test_nested_parent_shadow_does_not_detach_global](../tests/integration/test_codegen_calls.py#L88) | PASS |

## Behavior and test quality checks

- Scope lookup uses scope IDs and ancestor links, not depth alone. Parameters
  and body locals share the duplicate domain. All declarations are collected
  before uses; uncalled functions and return terms are still checked.
- Internal renaming is keyed by declaration identity. Source trees and public
  XML preserve original lexemes/IDs/links; semantic and type information live
  in side maps for downstream passes.
- Numeric scanning examines real TERM/NUM nodes, not operator-looking string
  text. Both mod/div anywhere reject with the specified message; any decimal
  NUM plus mod rejects even across unused/nested bodies. Whole-program float
  mode makes division of integer-looking literals fractional.
- Arithmetic captures operands in left-to-right order; self-reading assignment
  stores only after the complete RHS. Boolean `not` swaps destinations;
  `and`/`or` route to the RHS only when required. Pre/post while/until targets
  reevaluate conditions at the correct points.
- Child templates are prepared before their parents. Every copy receives fresh
  structural storage/labels; remapping uses declaration IDs, never raw text.
  Parent/grandparent/global captures survive cloning and repeated calls.
- Source failures are distinguished by phase/status. Input/output alias checks
  precede deletion; ordinary failed full compiles remove stale XML and target;
  successful publication uses temporary files and atomic replacement per file.
- The target inspector ignores comments/literals, checks one main/final return,
  declared storage, duplicate/dangling labels, prohibited ELSE/compositions
  and leftover runtime SPL calls. Native compile/run and exact stdout checks
  provide separate evidence beyond structural inspection.
- The 5,000 edge methods cover ten families, five whitespace layouts and all
  38 IDs. Their independently written algebra/truth/state expectations are
  checked through real subprocesses. Negative semantics are parser-valid;
  paired positives, fault positions, stale-output and recovery checks prevent
  a rejection in the wrong phase from counting as success. Missing C++ tools
  fail acceptance rather than silently skipping it.

## Validation recorded for this review

Local environment: macOS arm64, Python 3.14.0, Apple target C++ compiler.

| Check | Result and scope |
| --- | --- |
| Full baseline at the starting head | 1,218 methods passed, zero skips/failures/errors, 443.025 seconds. This includes the original 500 complete-system cases and numerical boundary anchors. |
| Changed release suite | 33/33 passed, including all 13 new regressions. The full current baseline is 1,231 methods; the previously passed baseline plus this focused suite covers that union, not a claimed new single 1,231-method run. |
| Current normal discovery | 6,231 unique methods: 1,231 baseline plus 5,000 edge methods. Discovery is an inventory check, not an execution result. |
| Independent packaged probes | 24/24 source-to-native-target executions passed using the exact downloaded macOS compiler. Three function levels, parameter shadowing, current-parent capture writes, repeated calls at the same loop call site, reversed arguments and signed/fractional inputs. Expected f(a,b)=3a+4b was calculated directly, not taken from compiler output or its reference evaluator. |
| Manual builder | Actual local LaTeX build remains five pages; newly emitted SHA-256 and size match the resulting PDF. Text/layout source is unchanged. The original CI PDF's five pages were visually checked in the preceding release verification. |
| Python compilation and whitespace | `compileall` for src/tests/tools/ci/packaging and `git diff --check` passed. |
| Prior hosted evidence at 9646447 | [All 32 push jobs](https://github.com/danieladegoede-ai/coco/actions/runs/40168686238) passed; [PR run](https://github.com/danieladegoede-ai/coco/actions/runs/40168688293) passed. Source baseline+5,000 on Windows/Linux; 5,000 exact-package cases on each of three OSs; 31/31 targets with each GNU 13 driver; extracted ZIP execution on all three. These are historical results for that commit. |
| Hosted evidence after review fixes | A fresh workflow must run on the pushed review head. Its actual result/artifact links belong on the PR; the old green result must not certify changed release tooling. |

The independent probe evidence is in ignored
`build/pr1-independent-probes.json`; its tested macOS binary hash is
`181048e05cae30fd62640709abc00d54c441e64eab244e0d80d2c8b8978a6126`.
Baseline and gate logs/reports are likewise ignored build outputs. The source
500/5,000 factories and inventories were not padded or relabelled for this
review.

## Remaining gates and practical limits

1. Fresh hosted checks for the review head must pass and produce a new candidate
   whose recorded commit and binary/manual hashes match. Do not mix its new
   manifest with the earlier candidate's files.
2. Every member must personally sign both declarations. Reinspect the final
   signed PDF and regenerate/check the actual submission archive and checksum.
3. Confirm the live upload cutoff and tutor platform, submit only in First
   Class, retain the portal receipt and verify the downloaded ZIP.

The Windows x64, Linux x64 and macOS arm64 builds have concrete CI evidence;
that does not prove an unspecified tutor OS/CPU. The numerical corpus uses
initialized bounded native int32/binary32 values and terminating programs.
Arbitrary precision, integer overflow, division by zero, unlimited expansion
and every possible machine resource size are not guaranteed by the supplied
sheets or by these tests. The explicit 1,000,000-instruction inlining resource
guard remains documented. These limits are not concealed as full coverage.

The reviewer found no remaining reproduced compiler defect in the stated
scope. The technical fixes and evidence are reviewable; A33's personal actions
and the new hosted run remain genuine outstanding release gates.
