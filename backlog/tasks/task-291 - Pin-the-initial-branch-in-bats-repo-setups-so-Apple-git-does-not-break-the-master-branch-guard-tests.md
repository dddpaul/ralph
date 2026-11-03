---
id: TASK-291
title: >-
  Pin the initial branch in bats repo setups so Apple git does not break the
  master-branch-guard tests
status: Done
assignee: []
created_date: '2026-11-03T17:32:00Z'
updated_date: '2026-11-03T18:30:00Z'
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
- [x] #1 setup_git_repo in tests/unit/pretools-hooks.bats creates its repo on master explicitly (git init -b master or -c init.defaultBranch=master)
- [x] #2 The git init calls in tests/unit/commit-msg-hook.bats and tests/unit/post-commit-hook.bats also pin the initial branch, and grep finds no bare git init left in tests/unit/*.bats
- [x] #3 LC_ALL=C bats tests/unit and uv run pytest pass
- [x] #4 On the macOS host, PATH="/usr/bin:/bin:/opt/homebrew/bin:$PATH" LC_ALL=C bats tests/unit (Apple git first on PATH) has no failures; the result is recorded in the task notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add -b master to the three bare git init calls in tests/unit (pretools-hooks setup_git_repo, commit-msg-hook, post-commit-hook); run bats + pytest; simulate Apple git's main default with GIT_CONFIG_GLOBAL init.defaultBranch=main since the container has no macOS host.

Commit: `d290dac` - task-291: pin the initial branch to master in bats repo setups

AC3: LC_ALL=C bats tests/unit gives 198/199 and pytest gives 1011 passed, 3 skipped, 4 xfailed; ruff is clean. The one bats failure, #185 (R11 settings.local.json shape), also fails on master: it compares this container's gitignored local .claude/settings.local.json, so it is environmental and unrelated to this change.
AC4 is DEFERRED to the macOS host, because this Linux container has git 2.39.5 and no Apple git. Host command: PATH="/usr/bin:/bin:/opt/homebrew/bin:$PATH" LC_ALL=C bats tests/unit. Stand-in: GIT_CONFIG_GLOBAL pointing at a file with init.defaultBranch=main. Under it, master fails #76 (master-branch-guard: blocks edit on master to non-allowlisted path), which reproduces the bug; task-291 passes #76, and only the environmental #185 remains.

Review: task-reviewer APPROVED (score 10) on the second pass. AC4 is still unchecked until the host run is recorded.

macOS host verification (after merge, master 0.14.13). The AC #4 command as written, PATH=/usr/bin:/bin:/opt/homebrew/bin:$PATH, puts more than Apple git first: it also selects /bin/bash 3.2 and Apple python3 3.9. Run outside the sandbox (inside it, Apple's python3 shim and diff fail on 'Operation not permitted'), it shows 203 tests with 6 failures, all in tests/unit/pre-commit-hook.bats. They come from the shipped git pre-commit hook: its declare -A at line 70 (since TASK-136) is invalid in bash 3.2, so under /bin/bash the hook exits 2. That is unrelated to this task and is reported to the owner as a separate finding. With only git swapped to Apple git 2.50.1 (a shim dir holding a git symlink to /usr/bin/git, first on PATH), LC_ALL=C bats tests/unit gives 203/203. The pre-TASK-291 pretools-hooks.bats (7dfeb3a) under the same shim fails 'master-branch-guard: blocks edit on master to non-allowlisted path', so this task fixes exactly the git-dependent failure. AC #4 is checked on that basis, with the deviation recorded here.
<!-- SECTION:NOTES:END -->
