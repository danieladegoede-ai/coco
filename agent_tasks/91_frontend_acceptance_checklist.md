# Front-end acceptance checklist

This is the shared completion checklist. An AI assistant must not describe the
front end as complete while a required item is unchecked or untested.

## Repository and contracts

- [ ] All four members approved the decisions.
- [ ] Shared contracts match the code.
- [ ] Each owned module has focused tests.
- [ ] No unapproved runtime dependency exists.
- [ ] No generated input/output or executable is committed.

## Source and lexer

- [ ] Plain ASCII input is loaded correctly.
- [ ] Non-ASCII input is rejected clearly.
- [ ] Every keyword and punctuation token is covered.
- [ ] Valid and invalid numbers are covered.
- [ ] Valid and invalid names are covered.
- [ ] Valid and invalid strings are covered.
- [ ] Token separator rules are covered.
- [ ] SP, CR, LF and CRLF provisional behaviour is covered.
- [ ] Positions remain correct after every newline form.
- [ ] Literal `$` is rejected.
- [ ] Exactly one internal EOF token is produced.

## Parser

- [ ] Every grammar production has a positive test.
- [ ] Every nullable production has a test.
- [ ] Assignment/call lookahead is covered.
- [ ] Name-term/call lookahead is covered.
- [ ] Every arithmetic, boolean and comparison form is covered.
- [ ] Both loop forms and branches are covered.
- [ ] Nested functions and nested control flow are covered.
- [ ] Missing/incorrect delimiters and keywords are rejected.
- [ ] Unexpected EOF and trailing input are rejected.
- [ ] Errors contain position, unexpected token, expected set and hint.

## Tree and XML

- [ ] Exactly one `SPL_PROG` root exists.
- [ ] Every node ID is unique and deterministic.
- [ ] Every non-root node has one valid parent.
- [ ] Parent and child links are symmetric.
- [ ] Child order follows grammar/input order.
- [ ] No cycles, dangling IDs or unreachable nodes exist.
- [ ] XML contents are escaped.
- [ ] XML is well formed and browser-readable.
- [ ] Repeated input gives byte-stable output.
- [ ] Failure cannot publish stale or partial output.

## Generated and black-box testing

- [ ] Generator has depth and size limits.
- [ ] Every grammar production is generated.
- [ ] Generated tests record reproducible seeds.
- [ ] Every generated valid program parses.
- [ ] One-fault mutations are rejected sensibly.
- [ ] Empty, small, large and deeply nested cases are covered.
- [ ] Missing/unreadable input is covered.
- [ ] Repeated execution and output replacement are covered.

## Executable and submission

- [ ] Target operating system and CPU are confirmed.
- [ ] Exact run command and filenames are confirmed.
- [ ] Exact upload format and URL are confirmed.
- [ ] Executable is built on the target platform.
- [ ] Clean-machine test passes without development tools.
- [ ] All four members run the release candidate.
- [ ] Release checksum is recorded.
- [ ] Submission is uploaded before the deadline.
- [ ] Downloaded submission is retested.
- [ ] Submission proof is saved.
