---
id: TASK-291
title: >-
  Pin the initial branch in bats repo setups so Apple git does not break the
  master-branch-guard tests
status: To Do
assignee: []
created_date: '2026-11-03T17:32:00Z'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

On the macOS host, `tests/unit/pretools-hooks.bats` case "master-branch-guard: blocks edit on master to non-allowlisted path" fails whenever Apple's git (`/usr/bin/git`, 2.50 Apple Git-155) comes before Homebrew's on PATH.

The root cause is the test, not the guard:
- `setup_git_repo` runs a bare `git init`.
- With no `init.defaultBranch` configured, Apple git names the first branch `main`, while Homebrew git 2.56 names it `master`.
- `master-branch-guard.sh` acts only on a branch named `master` (`if [ "$branch" != "master" ]; then exit 0; fi`), so on `main` it exits silently, and the test's deny assertions fail.
- Reproduced: `/usr/bin/git init` gives branch `main`, and the guard prints nothing for an Edit of README.md there.

Fix: pin the initial branch wherever a bats setup creates a repo, so the suite does not depend on the machine's git build or global config:

```bash
git init -b master "$TEST_DIR/repo" >/dev/null 2>&1
```

`tests/unit/commit-msg-hook.bats` and `tests/unit/post-commit-hook.bats` also run a bare `git init -q`. They do not assert on the branch name today, but pin them too for hermeticity.

## Scope

Out of scope:
- Changing `master-branch-guard.sh` to also protect `main`. The Ralph workflow (CLAUDE.md template, merge and tag steps) assumes `master`, and ralph-init creates new repos with `git init -b master`. Supporting `main` is its own decision.
- tests/python, which has no `git init` that depends on the branch name.

## Files

- `tests/unit/pretools-hooks.bats` (exists): `setup_git_repo`
- `tests/unit/commit-msg-hook.bats` (exists)
- `tests/unit/post-commit-hook.bats` (exists)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 setup_git_repo in tests/unit/pretools-hooks.bats creates its repo on master explicitly (git init -b master or -c init.defaultBranch=master)
- [ ] #2 The git init calls in tests/unit/commit-msg-hook.bats and tests/unit/post-commit-hook.bats also pin the initial branch, and grep finds no bare git init left in tests/unit/*.bats
- [ ] #3 LC_ALL=C bats tests/unit and uv run pytest pass
- [ ] #4 On the macOS host, PATH="/usr/bin:/bin:/opt/homebrew/bin:$PATH" LC_ALL=C bats tests/unit (Apple git first on PATH) has no failures; the result is recorded in the task notes
<!-- AC:END -->
