---
id: TASK-308
title: Reconcile uncertain shared-backlog creates and keep recovery refs
status: In Progress
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-06T14:19:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-307
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make create safe on lost races and uncertain pushes.

Retries:
- After a lost race, it reallocates with the same operation ID.
- After an uncertain push, it reconciles against origin by operation ID, and never allocates again without that check.

Recovery:
- A refs/ralph/recovery ref keeps an uncertain commit.
- Every temporary worktree is removed on every exit.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-014.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 After a non-fast-forward rejection, create reallocates in a fresh worktree with the same operation ID, at most 3 times
- [x] #2 After an uncertain push, create fetches and looks for its operation ID on origin and, if found, reports that ID, path and SHA as the result
- [x] #3 If reconciliation fails, create stops without allocating again
- [x] #4 Before removing a worktree whose commit acceptance is uncertain, create stores the commit under refs/ralph/recovery/(op-id) and prints how to finish or drop it
- [x] #5 Every temporary worktree is removed on every exit (success, failure, deadline, signal) after any recovery ref is saved
- [x] #6 Tests show an ambiguous push that origin accepted is not repeated, a failed reconciliation stops, and the recovery ref survives worktree removal
- [x] #7 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: rework cmd_create into its own loop: fresh worktree per attempt; non-fast-forward = definite loss → refetch + reallocate with same OP_ID (≤3 pushes); any other failed push = uncertain → fetch and grep CREATE_BASE..origin/master for the Shared-Backlog-Op trailer (found → report ID/path/SHA; fetch fails → exit 2 without reallocating; not found → retry after unreachable, stop after rejection). Before each push write $CREATE_TMP/uncertain (sha op id); the main shell creates CREATE_TMP and its EXIT trap runs create_cleanup, which saves refs/ralph/recovery/<op> from that file and prints check/drop/finish commands before removing the worktree — so deadline and signal kills are covered. on_signal now waits for the child group. New tests/shell/shared-backlog-recovery-test.sh (+ pytest harness) uses an origin post-receive hook that kills the client git push after the ref update to make an accepted-but-ambiguous push.

AC #7 (host): container /bin/bash is 5.2, so the bash 3.2 run of test_bash32_syntax skips; on a Mac host run /bin/bash tests/shell/shared-backlog-recovery-test.sh (and the create/retry/lock/claim suites). bash -n, the static bash-4 builtin guard and all shell suites pass under bash 5.2. ruff: 53 pre-existing findings on master, none new.

Commit: `5e8ee41` - task-308: reconcile uncertain shared-backlog creates and keep recovery refs
<!-- SECTION:NOTES:END -->
