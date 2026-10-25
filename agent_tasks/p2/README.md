# P2 AI work guide - 18 October 2026

Start with [00_START_HERE.md](00_START_HERE.md), then read your packet:

- [Rudolph: foundation, names, final release](10_u20598425_foundation_names_release.md)
- [Kuda: numeric policy, types, semantic generator and adversarial cases](20_u20620111_types_numeric_tests.md)
- [Cherise: target IR, arithmetic, Boolean/loop generation and verification](30_u21434019_codegen_verification.md)
- [Michele: templates, inlining, full driver and native release](40_u21448842_inlining_driver_release.md)

Shared reading: [interfaces and provisional decisions](05_SHARED_INTERFACES.md),
[handoff and final acceptance](90_HANDOFF_AND_ACCEPTANCE.md), root AGENTS.md,
the live [P2 tracker #20](https://github.com/RudolphLamp/coco/issues/20), and
the official 2026 sheets relevant to the selected issue.

The purpose is a correct runnable 1st Class compiler. Current documentation
does not assert that pending code, tutor decisions, reviews or release gates
are complete. PR #37 has the foundation and PR #38 the name pass; inspect their
live state and branch content before deciding where implementation starts.
