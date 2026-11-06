---
id: TASK-305
title: Make shared-backlog claims and the duplicate check exact
status: Done
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-06T13:32:00Z'
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
- [x] #1 claim treats a bare @claude assignee as unassigned
- [x] #2 A task with any assignee other than the holder, alone or among several, counts as taken
- [x] #3 A claim the holder already holds is still checked for To Do status and Done dependencies
- [x] #4 The holder comes from --as, else SHARED_BACKLOG_HOLDER, else git config ralph.holder, and a missing holder is an error
- [x] #5 check-dupes REV reads the task prefix and config from the REV tree, includes drafts and passes explicitly when REV has no backlog directory
- [x] #6 check-dupes fails when the backlog executable is missing
- [x] #7 --help prints the whole help including exit codes and exits 0
- [ ] #8 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: in plugins/ralph/scripts/shared-backlog.sh resolve the holder --as > SHARED_BACKLOG_HOLDER > git config ralph.holder (missing = error, @claude refused as holder); add real_assignees/other_assignees/held_by_holder so a bare @claude is unassigned and any other assignee besides the holder means taken; run the To Do and dependency checks before accepting an already-held claim; check-dupes REV reads the prefix via git show REV:backlog/config.yml, adds a draft ID check (backlog/drafts + archive/drafts, fixed prefix draft), passes with a message when REV has no backlog/, and fails when backlog is not on PATH; --help prints the whole header via awk to stdout and exits 0 before any git call. New scratch-repo suite tests/shell/shared-backlog-claim-test.sh plus pytest runner.

Commit: `3f68c18` - task-305: make shared-backlog claims and the duplicate check exact

AC #8 (host) deferred: this Linux container has no /bin/bash 3.2. On a Mac, run: /bin/bash tests/shell/shared-backlog-claim-test.sh && /bin/bash tests/shell/shared-backlog-lock-test.sh (both must end with failed: 0). The bash -n check, the bash 3.2 static guard (tests/python/test_bash32_syntax.py) and both shell suites pass here.

Commit: `42e8f90` - task-305: print the help from any directory and keep the static guard clean

Verified: claim suite 49 passed, lock suite 65 passed, full pytest 1303 passed / 4 skipped (bash 3.2 static guard included), bash -n clean. ruff check . reports 53 pre-existing errors in untouched files, identical on clean master; the new Python file is clean. task-reviewer: APPROVED (score 10) after fixing 3 first-pass findings (a static-guard false positive in the help test, the missing AC #8 host deferral note, and help not found when run by relative path from a subdirectory).

Commit: `e2917fd` - task-305: bump plugin version to 0.20.3 (patch)
<!-- SECTION:NOTES:END -->
