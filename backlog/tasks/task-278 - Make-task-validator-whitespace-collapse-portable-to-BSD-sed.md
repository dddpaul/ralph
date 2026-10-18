---
id: TASK-278
title: Make task-validator whitespace collapse portable to BSD sed
status: Done
assignee: []
created_date: '2026-10-17 16:30'
updated_date: '2026-10-18 09:18'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

`task-validator.sh` check #4 ("Duplicate acceptance criteria detected") normalizes AC text before comparing, and its whitespace-collapse step is `sed 's/[[:space:]]\+/ /g'`. `\+` in a basic regex is a GNU extension; macOS `/usr/bin/sed` reads it as a literal `+`, so runs of whitespace are never collapsed and two ACs that differ only in spacing are not reported as duplicates. The hook runs on the host, which for most Ralph users is macOS. This breaks R-INFRA-3 (GNU/BSD portability).

Measured from mycloud on 2026-10-17 with macOS `/usr/bin/sed`: the four ACs `Foo  bar`, `foo bar`, `other<TAB>thing`, `other thing` normalize to 4 unique with the current line and to 2 unique with `sed -E 's/[[:space:]]+/ /g'`; busybox `sed -E` also gives the collapsed result. mycloud carries the one-line fix locally under a `.claude/managed-file-drift.accept` entry, which lapses once this template changes.

## Scope

In scope:
- Replace `sed 's/[[:space:]]\+/ /g'` with `sed -E 's/[[:space:]]+/ /g'` on line 56 of the task-validator template and of this repo's own copy (template parity).
- A regression test that feeds whitespace-only duplicate ACs through the validator with the host's own `sed` and asserts the duplicate is reported.

Out of scope:
- Any other change to the validator's checks or the LLM rubric.
- Other scripts (a grep of `plugins/` and `.claude/hooks/` on 2026-10-17 found no other GNU-only `\+`/`\?`/`\|` in a basic-regex `sed`).

## Files

- `plugins/ralph/skills/ralph-init/templates/claude/hooks/task-validator.sh` (exists) - line 56.
- `.claude/hooks/task-validator.sh` (exists) - same line, kept identical to the template.
- `tests/unit/template-parity.bats` (exists) - must keep passing.
- a new or existing validator test under `tests/` (to-create or exists) - the whitespace-duplicate regression case.

## Source

Source: /Users/paul/Private/Projects/mycloud@bca1c9db3778-dirty
Source context (read-only, do NOT modify): /Users/paul/Private/Projects/mycloud/backlog/tasks/task-60 - Upgrade-myclouds-ralph-files-to-the-current-ralph-init-template.md (the review finding and the measurement are in its notes)

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior - not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Neither plugins/ralph/skills/ralph-init/templates/claude/hooks/task-validator.sh nor .claude/hooks/task-validator.sh contains the GNU-only pattern sed 's/[[:space:]]\+/ /g'; both collapse whitespace with sed -E 's/[[:space:]]+/ /g' (grep)
- [x] #2 A test runs task-validator.sh against a task whose ACs differ only in whitespace (e.g. 'Foo  bar' and 'foo bar') using the host sed and asserts the output reports 'Duplicate acceptance criteria detected'; it fails against the old line on macOS sed
- [x] #3 tests/unit/template-parity.bats passes
- [x] #4 uv run pytest and uv run ruff check . pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: switch line 56 whitespace collapse to sed -E 's/[[:space:]]+/ /g' in the live hook and the ralph-init template; add tests/unit/task-validator.bats running both copies on whitespace-only duplicate ACs, plus a case under a BSD-BRE sed shim (BRE '\+' read as literal '+') so the regression is caught on GNU hosts too.

Commit: `2083e82` - task-278: collapse AC whitespace with portable sed -E in task-validator

Commit: `dbda63a` - task-278: restore the execute bit on both task-validator copies

Line 56 of both task-validator.sh copies now collapses whitespace with sed -E 's/[[:space:]]+/ /g'. New tests/unit/task-validator.bats (4 tests) runs both copies on ACs that differ only in whitespace; test 3 runs under a sed shim that reads BRE '\+' as a literal '+' (like macOS /usr/bin/sed), and it fails against the old line on GNU hosts too. Real macOS sed could not be run in the container. template-parity.bats: 11/12; the only failure (settings.local.json shape) reads the gitignored, container-local .claude/settings.local.json and also fails on master. pytest 913 passed, ruff clean. task-reviewer: APPROVED after the execute bit was restored (sed -i on this mount had dropped it).

Commit: `576d4a9` - task-278: bump plugin version to 0.14.6 (patch)
<!-- SECTION:NOTES:END -->
