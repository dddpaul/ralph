---
id: TASK-292
title: Gate the commit guards on commits after shell keywords in the jq lexer
status: To Do
assignee: []
created_date: '2026-11-03T17:32:00Z'
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
- `tests/unit/pretools-hooks.bats` (exists)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The four xfail-marked cases of test_guards_see_commit_after_shell_syntax in tests/python/test_commit_guards.py (prefixes 'if true; then ', 'if false; then :; else ', '{ ', '! ') pass with their xfail marks removed: both guards deny the bad commit after each prefix
- [ ] #2 Matching bats cases in tests/unit/pretools-hooks.bats pass, the identical-lexer bats case passes, and the .claude/hooks copies of both guards are byte-identical to the templates
- [ ] #3 A command that only mentions the two-word phrase after a keyword, such as if true; then echo "G<SP>C"; fi, is still allowed by both guards (a bats case)
- [ ] #4 Both guards pass bash -n and satisfy R-INFRA-3; uv run pytest, uv run ruff check . and LC_ALL=C bats tests/unit pass
- [ ] #5 On the macOS host, tests/unit/pretools-hooks.bats passes with /bin/bash 3.2 first on PATH; the result is recorded in the task notes
<!-- AC:END -->
