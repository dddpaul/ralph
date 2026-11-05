---
id: TASK-311
title: Refuse pushes that carry duplicate task IDs with a plugin pre-push body
status: To Do
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-05T04:55:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-297
  - TASK-305
  - TASK-307
  - TASK-308
  - TASK-310
  - TASK-322
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
<!-- AC:END -->
