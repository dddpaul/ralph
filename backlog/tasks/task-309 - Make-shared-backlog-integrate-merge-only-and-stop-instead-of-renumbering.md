---
id: TASK-309
title: Make shared-backlog integrate merge-only and stop instead of renumbering
status: Done
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-06T14:56:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-304
  - TASK-305
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make integrate merge origin and publish safely.

Merge and policy:
- It merges, never rebases, and writes an Integrated-Origin trailer.
- Its policy is fixed at invocation from the HEAD before the merge.
- It fails before merging when checks or their context are missing.

Duplicates: it stops with an old-to-new mapping and never renumbers.

Interruptions: it preserves an interrupted merge.

Retries: it retries only on a non-fast-forward rejection.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-015 and FR-9.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 integrate merges origin/master, never rebases, and its merge commit carries an Integrated-Origin trailer naming the fetched origin SHA
- [x] #2 integrate takes its opt-in and checks policy from the pre-merge HEAD, fixed at invocation; tests cover merged-in commits that change checks and that remove the marker
- [x] #3 integrate fails before merging when no checks are configured or their execution context is missing
- [x] #4 On duplicate IDs integrate stops with an old-to-new mapping and neither pushes nor renumbers
- [x] #5 An interrupted merge is preserved rather than reset, and a retry first checks for a clean state
- [x] #6 integrate retries a push only on a non-fast-forward rejection, at most 3 times, and reports auth, hook and unreachable failures without retrying
- [ ] #7 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: integrate reads opt-in (sharedBacklog) and checks from HEAD:.claude/ralph.json via jq before fetching, fixed for all retries; $SHARED_BACKLOG_CHECKS overrides checks; new $SHARED_BACKLOG_CHECKS_EXEC prefix is probed before merging (execution context), and backlog must be on PATH. Refuse to start while a merge/rebase/cherry-pick/index.lock is left (report git_state, never reset). Merge the fetched origin SHA with an Integrated-Origin trailer. Factor renumber's ID choice into renumber_plan; integrate prints that old-to-new mapping and stops on duplicates (merge commit kept, nothing pushed). Drop renumber --amend. push_master records a failure class (non-fast-forward/auth/hook/unreachable); integrate retries only non-fast-forward, max 3. New tests/shell/shared-backlog-integrate-test.sh + pytest harness.

Commit: `06e155d` - task-309: make integrate merge-only and stop on duplicate IDs

AC7: bash -n, the bash 3.2 static guard (test_bash32_syntax) and all shared-backlog shell suites pass in the devcontainer; the /bin/bash 3.2 runtime check is host-only (skipped here: /bin/bash is 5.2) and still needs a host run.

Host follow-up for AC7: on the Mac run /bin/bash tests/shell/shared-backlog-integrate-test.sh (and the claim, create, lock, recovery and retry suites); each must end 'failed: 0'.
Implemented: integrate policy from pre-merge HEAD (.claude/ralph.json sharedBacklog + checks, SHARED_BACKLOG_CHECKS override, SHARED_BACKLOG_CHECKS_EXEC context probe, jq and backlog required); merge of the fetched origin SHA with Integrated-Origin trailer; duplicate stop prints renumber_plan mapping (shared with manual renumber; --amend removed); require_settled refuses over a left merge/rebase/cherry-pick/revert/index.lock; push_master sets PUSH_FAILURE and integrate retries only non-fast-forward (max 3). Tests: tests/shell/shared-backlog-integrate-test.sh (82 checks) via tests/python/test_shared_backlog_integrate.py. Review: APPROVED 06e155d
<!-- SECTION:NOTES:END -->
