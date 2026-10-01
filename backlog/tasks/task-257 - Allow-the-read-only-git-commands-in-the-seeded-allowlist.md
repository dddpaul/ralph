---
id: TASK-257
title: Allow the read-only git commands in the seeded allowlist
status: Done
assignee: []
created_date: '2026-10-01 06:34'
updated_date: '2026-10-01 07:01'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The seeded allowlist in `plugins/ralph/skills/ralph-init/templates/claude/settings.local.json` carries seven git rules, and every one is a **write**:

```
Bash(git add:*)  Bash(git commit:*)  Bash(git config:*)  Bash(git checkout:*)
Bash(git merge:*)  Bash(git mv:*)  Bash(git rm:*)
```

Not one read-only git command is allowed. `git log`, `git status`, `git diff`, `git show`, `git rev-parse` and `git ls-files` all fall through to `autoAllowBashIfSandboxed`. That is backwards from a safety standpoint — the mutating commands are pre-approved and the harmless ones are not — and it only ever made sense while auto-allow was assumed to cover reads.

Observed 2026-10-01: an interactive compound command that ran a plugin helper and then `git log` / `git status` / `git tag` prompted the user, while the same helper call alone did not. TASK-254 measured auto-allow covering the bare helper call on Claude Code 2.1.280; it does **not** follow that every read-only command in every command shape is covered, and this allowlist gap is the part we control.

A headless `claude -p` A/B (sandbox enabled, empty allowlist) did not reproduce the prompt — non-interactive mode resolves these differently — so the reproduction is interactive-only. Do not treat a clean headless run as evidence the gap is closed.

## Scope

Add six narrow, non-mutating rules to the template allowlist:

```
Bash(git log:*)  Bash(git status:*)  Bash(git diff:*)
Bash(git show:*)  Bash(git rev-parse:*)  Bash(git ls-files:*)
```

Apply the same six to this repo's live `.claude/settings.local.json`, which is gitignored (so it will not appear in the diff) but is kept equal to the template in practice.

## Deliberately excluded

`git tag` and `git branch` are **not** read-only, despite looking like query commands:

- `Bash(git tag:*)` would also permit `git tag -d v0.8.4` — deleting a release tag.
- `Bash(git branch:*)` would also permit `git branch -D <name>` — deleting an unmerged branch.

Both are destructive and must keep prompting. The merge flow in CLAUDE.md step 6 already has the narrow write rules it needs. Do not add these two, and do not add a blanket `Bash(git:*)` — R6 forbids it.

## Note on R6

All six additions are narrow subcommand prefixes with no interpreter and no mutation path, so R6 is satisfied. Check each one actually cannot modify the repository before adding it; two commands that looked read-only during planning were not.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The template settings.local.json allows exactly these six: git log, git status, git diff, git show, git rev-parse, git ls-files
- [x] #2 The template allowlist contains no Bash(git tag:*), no Bash(git branch:*) and no blanket Bash(git:*)
- [x] #3 This repo's live .claude/settings.local.json carries the same six rules, so its allow set still equals the template's
- [x] #4 A test asserts every git rule in the template is a named subcommand prefix, and fails if a blanket Bash(git:*) or a mutating subcommand such as tag or branch is added
- [x] #5 LC_ALL=C bats tests/unit passes, including the R11 settings.local.json shape test
- [x] #6 uv run ruff check . and uv run pytest both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `9efe593` - task-257: allow the read-only git queries in the seeded allowlist

Plan: add the six read-only git prefix rules to the template (after the write rules) and the live gitignored settings.local.json (sorted); add tests/python/test_git_allow_rules.py asserting every template git rule is a named subcommand from a vetted read/write set and that tag/branch/blanket are absent.

Implemented: six read-only git prefix rules added to the template and the live (gitignored) settings.local.json; allow sets equal. New tests/python/test_git_allow_rules.py pins every template git rule to a vetted named subcommand (mutation-checked: git:*, tag, branch, push each fail). Residual: git log/diff/show accept --output=<file>, verified to write a file; a prefix rule cannot exclude a flag, the sandbox write boundary bounds it (noted in the test docstring). Gates: ruff clean, pytest 685 passed, bats tests/unit 110/110 (via node_modules/.bin/bats). task-reviewer: APPROVED.

Commit: `76cf507` - task-257: bump plugin version to 0.8.5 (patch)
<!-- SECTION:NOTES:END -->
