# Release decisions after Announcement 34 (25 October 2026)

The Speaker authorized completing native builds, documentation and release
verification on `danieladegoede-ai/coco`. The tested P2 source is imported from
`RudolphLamp/coco` at `c2fb92c`; both repository histories are preserved.

| Prior question | Release disposition and basis |
| --- | --- |
| D01 C/C++ / filename / toolchain | **Resolved by supplied A34:** C++ designation is accepted; keep human-readable `program.cpp`; prefer `g++ -std=c++17`. CI also uses GNU 13's `gcc -x c++ ... -lstdc++`. Actual tool versions are recorded; no exact uninstalled 13.0.0 version is claimed. |
| D02 formal/actual direction | Adopt cloned formal = captured actual. This is the working inlining interpretation; reverse assignment loses supplied values. Nonzero/multiple-argument execution tests cover it. It is not presented as a newly received tutor answer. |
| D03 Boolean transfers | Adopt explicit true and false comparison/goto destinations; no executable else/Boolean composition. This implements the required behavior robustly for nested not/and/or. |
| D04 arity/evaluation | Adopt matching formal/actual count, left-to-right full actual capture, short-circuit Boolean evaluation. These are documented implementation choices under the sheets' translation guidelines; do not invent a tutor approval. |
| D05 numbers/output | Follow explicit global conflicts; int unless div/decimal selects float; native int32/binary32 on configured targets; standard cout formatting. No arbitrary precision/overflow/divide-by-zero guarantee or new lexical range rejection. |
| D06 namespaces/returns | Preserve separate variable/function namespaces and body-scope returns; tested lexical identities drive inlining. No additional unrequested naming restriction. |
| D07 extra outputs | Publish original `tree.xml` and readable `program.cpp`; keep internal symbol/type maps. Supplied sources specify no additional public symbol-table schema. |
| D08 platforms/names/portal | Deliver Windows x64 `.exe`, Linux x64 `group-2` (no extension), supplemental macOS arm64 `macos/group-2`. A33 requires First Class-only upload and two personal declarations. The portal closing hour and actual upload/receipt cannot be fabricated. |

The user asked to tick all names as approving. A33 specifically requires each
member's **personal signature on each of two declarations**. No other member's
consent/signature was supplied, so the manual leaves eight signature lines
blank and the candidate manifest says `submission_ready: false`. This is a
record of actual status, not an extra approval requirement invented by a tool.

The CI/CD pipeline publishes a **draft candidate** only after source tests,
three native builds, exact packaged-binary case coverage, GNU 13 compatibility,
manual checks, hash verification and extracted-archive tests. It never uploads
to ClickUp or claims personal approvals. A final signed manual and verified
First Class portal receipt remain personal release actions.
