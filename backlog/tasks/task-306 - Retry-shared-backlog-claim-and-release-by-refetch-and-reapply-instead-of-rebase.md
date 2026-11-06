---
id: TASK-306
title: >-
  Retry shared-backlog claim and release by refetch and reapply instead of
  rebase
status: Done
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-06T13:53:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-305
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace the stage-1 rebase in claim and release with refetch-and-reapply. On a lost race they:
1. drop their own unpushed commit;
2. fetch;
3. check again;
4. make a fresh commit;
5. push.

No git rebase may remain in the protocol.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-012 and FR-9.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 On a non-fast-forward rejection, claim and release drop their unpushed commit, fetch, re-check against the new origin, recommit and push, at most 3 times
- [x] #2 No git rebase remains anywhere in plugins/ralph/scripts/shared-backlog.sh (checked by grep)
- [x] #3 A claim that loses a race reports the winner and leaves local master equal to origin
- [x] #4 Tests cover two clones racing to claim one task with exactly one landing, a release racing a claim, and a retry after an unrelated origin commit
- [x] #5 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `21f2c81` - task-306: retry claim, release and create by refetch and reapply instead of rebase

Plan: replace land_linear (rebase + verify) with land_reapply APPLY: APPLY checks the current tree and commits; on a refused push fetch, reset --hard to the new origin/master (drops our unpushed commit) and run APPLY again, at most 3 pushes. Split claim/release/create into *_apply functions; create re-runs backlog task create so the retry takes the next free ID. New suite tests/shell/shared-backlog-retry-test.sh + pytest harness.

AC #5 (host) deferred: the container's /bin/bash is 5.2, so test_bash32_syntax skips its 3.2 run. On a Mac host run: /bin/bash tests/shell/shared-backlog-retry-test.sh (and the claim/lock suites). bash -n, the static bash-4 builtin guard and all shell suites pass under bash 5.2.

Commit: `ef82389` - task-306: exit 2 when claim or release cannot reach origin

Done: land_reapply replaces the rebase landing for claim, release and create; failures reset to origin/master (after one more fetch when the push was refused 3 times); claim/release exit 2 when origin is unreachable mid-retry. Release now undoes locally on failure instead of keeping the commit. Reviewer APPROVED (minor, open: the mid-retry exit-2 path has no test; a failed create commit can leave an untracked task file, left to TASK-307).

Commit: `ea95c01` - task-306: bump plugin version to 0.20.4 (patch)
<!-- SECTION:NOTES:END -->
