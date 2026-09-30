# Front-end agent work packets

These files let each member and their AI assistant understand the complete
front-end task without relying on GitHub issues.

## Current status

The allocation and interfaces were **approved by all four members on
22 September 2026**. Implementation may begin from the shared foundation on
`main`.

## Required shared reading

Every member and AI assistant must read:

1. `../README.md`
2. `../AGENTS.md`
3. `00_team_decisions.md`
4. `01_shared_contracts.md`
5. `02_spl_reference.md`
6. `90_integration_and_release.md`
7. `91_frontend_acceptance_checklist.md`
8. The member's individual packet

## Proposed equal allocation

| Student | Work packet | GitHub issue | Main result |
| --- | --- | --- | --- |
| `u20598425` | `10_u20598425_tree_xml.md` | [#8](https://github.com/RudolphLamp/coco/issues/8) | Validated syntax tree and deterministic `tree.xml` |
| `u20620111` | `20_u20620111_lexer.md` | [#9](https://github.com/RudolphLamp/coco/issues/9) | Correct token stream with locations and lexical errors |
| `u21434019` | `30_u21434019_parser.md` | [#10](https://github.com/RudolphLamp/coco/issues/10) | Complete grammar parser with useful syntax errors |
| `u21448842` | `40_u21448842_cli_testing_release.md` | [#11](https://github.com/RudolphLamp/coco/issues/11) | Runnable integrated front end and black-box test system |

Each packet contains implementation, tests, documentation and integration
responsibilities. Coordination alone does not count as a member's technical
work.

## How the work remains independent

- The lexer is tested without the parser.
- The parser is tested with manually constructed tokens.
- The tree and XML modules are tested with manually constructed nodes.
- The CLI and testing tools are developed against small stubs until the real
  modules are merged.
- Each member owns different source paths and different primary test files.
- Only the approved interfaces are shared.

## Expected branches

```text
feat/u20598425-tree-xml
feat/u20620111-lexer
feat/u21434019-parser
feat/u21448842-cli-testing
```

## Handoff format

When a member says a task is ready, include:

- branch and latest commit;
- owned files changed;
- tests added;
- exact verification commands and results;
- known limitations;
- provisional specification decisions used; and
- anything required from another module at integration time.

No work is considered handed off when it exists only on one person's computer.
