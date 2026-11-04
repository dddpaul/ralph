---
id: TASK-305
title: Make shared-backlog claims and the duplicate check exact
status: To Do
assignee: []
created_date: '2026-11-04T14:53:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-304
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make claims and the duplicate check exact.

Claims:
- A bare @claude assignee counts as unassigned; it is generic and names no host.
- Any other assignee besides the holder means taken.
- An already-held claim is still checked for status and dependencies.
- The holder comes from --as, then SHARED_BACKLOG_HOLDER, then git config ralph.holder.

check-dupes reads its config from the revision it checks, and includes drafts.

Also fix --help, which today stops at the Exit codes line and exits 64.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-011 and FR-6.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 claim treats a bare @claude assignee as unassigned
- [ ] #2 A task with any assignee other than the holder, alone or among several, counts as taken
- [ ] #3 A claim the holder already holds is still checked for To Do status and Done dependencies
- [ ] #4 The holder comes from --as, else SHARED_BACKLOG_HOLDER, else git config ralph.holder, and a missing holder is an error
- [ ] #5 check-dupes REV reads the task prefix and config from the REV tree, includes drafts and passes explicitly when REV has no backlog directory
- [ ] #6 check-dupes fails when the backlog executable is missing
- [ ] #7 --help prints the whole help including exit codes and exits 0
- [ ] #8 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->
