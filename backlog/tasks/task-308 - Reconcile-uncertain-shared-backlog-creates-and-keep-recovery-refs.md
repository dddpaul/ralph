---
id: TASK-308
title: Reconcile uncertain shared-backlog creates and keep recovery refs
status: Done
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-07T21:30:00Z'
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

Commit: `d37371d` - task-308: stop the deadline watchdog and remove its flag on a signal

Done: create reallocates in a fresh worktree with the same op ID after a non-fast-forward (≤3 pushes); any other failed push is reconciled against origin by the Shared-Backlog-Op trailer (found → reported as the result; unreachable → exit 2, no reallocation); an uncertain commit is kept as refs/ralph/recovery/<op-id> with check/drop/finish instructions, by the main shell's EXIT trap before it removes the worktree, so deadline and signal exits are covered. on_signal also stops the deadline watchdog and removes its flag. Tests: tests/shell/shared-backlog-recovery-test.sh via tests/python/test_shared_backlog_recovery.py. task-reviewer APPROVED (after a fix for the watchdog left running on a signal).

Commit: `4fae8ee` - task-308: mark Done

Commit: `e1df34c` - task-308: bump plugin version to 0.20.6 (patch)

Host check (macOS, /bin/bash 3.2.57 with nested bash also 3.2 through a PATH wrapper, master 18591c8, 2026-11-08): bash -n clean on the script and the shim; tests/python/test_bash32_syntax.py 15 passed, none skipped; tests/shell/shared-backlog-recovery-test.sh 52 passed, 0 failed, run outside the Claude Code sandbox (inside it the suite cannot kill the git push client, so 8 checks fail there). Records the AC #7 host clause deferred above.
<!-- SECTION:NOTES:END -->
