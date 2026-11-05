---
id: TASK-311
title: Refuse pushes that carry duplicate task IDs with a plugin pre-push body
status: To Do
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-05T07:17:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-297
  - TASK-305
  - TASK-307
  - TASK-308
  - TASK-310
  - TASK-322
  - TASK-302
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the plugin's pre-push body, which refuses a push carrying a duplicate task ID. A duplicate arrives with no git conflict, because the file names differ.

It acts on the trusted switch ralph.sharedBacklog, runs the read-only check-dupes on every pushed SHA without taking a lock, and chains (name).local.

It includes the end-to-end test: a real create push through the shim while create holds the lock, completing without deadlock.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-017.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 plugins/ralph/git-hooks/pre-push acts when ralph.sharedBacklog is true, buffers stdin, runs the read-only check-dupes on every pushed SHA without taking a lock, and skips ref deletions
- [ ] #2 Tests show it refuses a tip carrying a duplicate, including one in a draft, and refuses when backlog is missing
- [ ] #3 Tests show it passes a ref deletion and a push of several refs
- [ ] #4 It keeps enforcing after a commit that removes the marker while the clone switch is on
- [ ] #5 An existing hook keeps running as pre-push.local with the same stdin
- [ ] #6 An end-to-end test runs a real create push through the installed shim while create holds the protocol lock, and it completes without deadlock
- [ ] #7 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
- [ ] #8 This repo own pre-push (the version-bump guard) becomes pre-push.local behind the plugin pre-push shim, and a real push of a bumped commit to a scratch remote still runs the version-bump guard (moved here from TASK-302)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From the TASK-302 review (2026-11-05): moving this repo's pre-push behind the plugin pre-push shim (AC #8) needs either a managed-file-drift.accept entry for .git/hooks/pre-push, so that clone keeps it as pre-push.local, or a manual move. clone stops on a differing hook the accept file does not list. Added TASK-302 as a dependency, because the move assumes this repo is already migrated.
<!-- SECTION:NOTES:END -->
