---
id: TASK-306
title: >-
  Retry shared-backlog claim and release by refetch and reapply instead of
  rebase
status: In Progress
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-06T13:33:00Z'
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
- [ ] #1 On a non-fast-forward rejection, claim and release drop their unpushed commit, fetch, re-check against the new origin, recommit and push, at most 3 times
- [ ] #2 No git rebase remains anywhere in plugins/ralph/scripts/shared-backlog.sh (checked by grep)
- [ ] #3 A claim that loses a race reports the winner and leaves local master equal to origin
- [ ] #4 Tests cover two clones racing to claim one task with exactly one landing, a release racing a claim, and a retry after an unrelated origin commit
- [ ] #5 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->
