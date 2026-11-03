---
id: TASK-292
title: Gate the commit guards on commits after shell keywords in the jq lexer
status: Done
assignee: []
created_date: '2026-11-03T17:32:00Z'
updated_date: '2026-11-03T18:30:00Z'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-281 was implemented twice. One implementation, an awk lexer with pytest tests, was pushed to GitHub as v0.14.8 from another machine. The other, a jq lexer with bats tests verified on the macOS host, was merged locally. When the two masters were merged, the jq lexer was kept: it enforces the task prefix on `cat <<'MSG' | G<SP>C -F -` (the form this repo uses for multi-line messages), sees commits behind `env`/`command`/`time` wrappers, and handles attached `-S`/`-u` values, all of which the awk version misses. (`G<SP>C` stands for the two words "git" and "commit" separated by a space, as in TASK-281.)

The awk version's test suite was kept too. It found four forms the jq lexer does not gate: a commit after `if true; then `, after `if false; then :; else `, after `{ `, and after `! `. Both guards allow a forbidden trailer or a wrong prefix in those forms, because the program word they read is the shell keyword, not `git`. The four cases are marked `xfail(strict=True)` in `test_guards_see_commit_after_shell_syntax`, in this test file:

```text
tests/python/test_commit_guards.py
```

Fix: in the shared jq lexer, skip leading shell reserved words before reading the program word, the same way it already skips `env`/`command`/`time` wrappers and `VAR=value` assignments. The words are `if`, `then`, `else`, `elif`, `do`, `while`, `until`, `!` and `{`. Keep the lexer block byte-identical in both guards and in this repo's `.claude/hooks` copies.

## Scope

Out of scope:
- a commit inside `$( )` or backticks, which neither implementation gates;
- any change to the trailer or prefix policy.

## Files

- `plugins/ralph/skills/ralph-init/templates/claude/hooks/commit-prefix-guard.sh` (exists)
- `plugins/ralph/skills/ralph-init/templates/claude/hooks/commit-msg-guard.sh` (exists)
- `.claude/hooks/commit-prefix-guard.sh` and `.claude/hooks/commit-msg-guard.sh` (exist): keep identical to the templates
- `tests/unit/pretools-hooks.bats` (exists); `tests/python/test_commit_guards.py` (exists): remove the four xfail marks
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The four xfail-marked cases of test_guards_see_commit_after_shell_syntax in tests/python/test_commit_guards.py (prefixes 'if true; then ', 'if false; then :; else ', '{ ', '! ') pass with their xfail marks removed: both guards deny the bad commit after each prefix
- [x] #2 New bats cases for the four keyword prefixes are added to tests/unit/pretools-hooks.bats and pass, the identical-lexer bats case passes, and the .claude/hooks copies of both guards are byte-identical to the templates
- [x] #3 A command that only mentions the two-word phrase after a keyword, such as if true; then echo "G<SP>C"; fi, is still allowed by both guards (a bats case)
- [x] #4 Both guards pass bash -n and satisfy R-INFRA-3; uv run pytest, uv run ruff check . and LC_ALL=C bats tests/unit pass
- [x] #5 On the macOS host, tests/unit/pretools-hooks.bats passes with /bin/bash 3.2 first on PATH; the result is recorded in the task notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: extend the prog() skip list in the shared jq lexer with if/then/else/elif/do/while/until/!/{ in both template guards, copy to .claude/hooks, drop the four xfail marks, add bats cases (deny after each keyword prefix for both guards; allow a keyword block that only mentions the phrase).

Commit: `acb0fdc` - task-292: skip shell reserved words before the program word in the commit guards' lexer

AC5 is DEFERRED to the macOS host, because this Linux container has no /bin/bash 3.2. Host command: PATH="/bin:/usr/bin:$PATH" LC_ALL=C node_modules/.bin/bats tests/unit/pretools-hooks.bats. Follow-up: run that command on the host, record the result here, then check AC5. The keyword loops in the new bats cases assert with `|| false`, so a failing prefix fails the test under bash 3.2 errexit too. Container stand-in: bash 5 bats tests/unit/pretools-hooks.bats 77/77; full tests/unit 202/203, and the one failure (#189, R11 settings.local.json shape) also fails on master because of the untracked local .claude/settings.local.json.

Commit: `2b20a29` - task-292: make the keyword-loop bats asserts errexit-safe under bash 3.2

Review: task-reviewer APPROVED (score 10) on the second pass. Implemented: prog() in the shared jq lexer now also skips if/then/else/elif/do/while/until/!/{ before the program word, so both commit guards gate a commit after a shell keyword. AC5 stays unchecked until the host run is recorded.

Commit: `1dc6c4b` - task-292: bump plugin version to 0.14.13 (patch)

macOS host verification (after merge, master 0.14.13). With /bin/bash 3.2.57 first on PATH, LC_ALL=C bats tests/unit/pretools-hooks.bats gives 77/77. /bin/bash -n passes on both guard templates, and the .claude/hooks copies are byte-identical. uv run pytest on the host: 1014 passed / 4 skipped, with no xfail left in tests/python/test_commit_guards.py.
<!-- SECTION:NOTES:END -->
