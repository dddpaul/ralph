---
id: TASK-307
title: Allocate shared-backlog task IDs in an isolated temporary worktree
status: Done
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-07T21:30:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-297
  - TASK-306
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make create allocate in a detached temporary worktree at a freshly fetched origin/master, under the protocol lock. The ID is published before anyone sees it, whatever state the user's checkout is in: ahead, dirty or on a task branch.

The commit carries a Shared-Backlog-Op trailer with an operation ID that stays fixed across retries.

Offline, create refuses before allocating.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-013 and FR-8.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 create runs under the protocol lock in a detached temporary worktree at a freshly fetched origin/master
- [x] #2 create commits task-N: add task with a Shared-Backlog-Op trailer whose operation ID is fixed once per create and reused on every retry
- [x] #3 Hooks in the temporary worktree resolve the plugin with the original clone project identity, proven by a real commit made there
- [x] #4 With origin unreachable, create refuses before allocating with exit 2 and leaves no commit and no task file
- [x] #5 Tests run create in clones that are behind origin, ahead of it, dirty and on a task branch; each publishes an ID free on origin and leaves the user branch, index and working tree unchanged
- [x] #6 sync and integrate refuse while an untracked task file is in the working tree, and list it
- [x] #7 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: cmd_create fixes an op ID (new_token), fetches origin (exit 2 offline before any worktree/task file), adds a detached git worktree at origin/master under a mktemp dir, runs land_reapply create_apply there (commit 'task-N: add task' + Shared-Backlog-Op trailer), then removes the worktree; the user's branch, index and tree are never touched. Linked worktree shares the git common dir, so the shim's resolver keys on the original clone root. sync and integrate refuse while untracked task files exist and list them. New tests/shell/shared-backlog-create-test.sh (+ pytest harness) covers behind/ahead/dirty/task-branch clones, offline refusal, op-ID reuse across a refused push, untracked-file refusals and a real shim commit in the worktree against a project-scope registry entry.

Commit: `1101ac3` - task-307: allocate shared-backlog task IDs in a temporary worktree

AC #7 (host) deferred: the container's /bin/bash is 5.2, so test_bash32_syntax skips its 3.2 run. On a Mac host run: /bin/bash tests/shell/shared-backlog-create-test.sh (and the retry/claim/lock suites). bash -n, the static bash-4 builtin guard and all shell suites pass under bash 5.2.

Commit: `f55ca7d` - task-307: note that claim and release refuse on untracked task files too

Done: create allocates in a detached worktree at a freshly fetched origin/master under the protocol lock, commits task-N: add task with a Shared-Backlog-Op trailer (op ID fixed per create), refuses offline with exit 2 before allocating; sync/integrate (and so claim/release) refuse on untracked task files. Tests: tests/shell/shared-backlog-create-test.sh via tests/python/test_shared_backlog_create.py. task-reviewer APPROVED.

Commit: `d4161cc` - task-307: bump plugin version to 0.20.5 (patch)

Host check (macOS, /bin/bash 3.2.57 with nested bash also 3.2 through a PATH wrapper, master 18591c8, 2026-11-08): bash -n clean on the script and the shim; tests/python/test_bash32_syntax.py 15 passed, none skipped; tests/shell/shared-backlog-create-test.sh 56 passed, 0 failed. Records the AC #7 host clause deferred above.
<!-- SECTION:NOTES:END -->
