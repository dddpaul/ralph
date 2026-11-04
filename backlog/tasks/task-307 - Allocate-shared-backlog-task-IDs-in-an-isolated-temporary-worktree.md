---
id: TASK-307
title: Allocate shared-backlog task IDs in an isolated temporary worktree
status: To Do
assignee: []
created_date: '2026-11-04T14:53:00Z'
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
- [ ] #1 create runs under the protocol lock in a detached temporary worktree at a freshly fetched origin/master
- [ ] #2 create commits task-N: add task with a Shared-Backlog-Op trailer whose operation ID is fixed once per create and reused on every retry
- [ ] #3 Hooks in the temporary worktree resolve the plugin with the original clone project identity, proven by a real commit made there
- [ ] #4 With origin unreachable, create refuses before allocating with exit 2 and leaves no commit and no task file
- [ ] #5 Tests run create in clones that are behind origin, ahead of it, dirty and on a task branch; each publishes an ID free on origin and leaves the user branch, index and working tree unchanged
- [ ] #6 sync and integrate refuse while an untracked task file is in the working tree, and list it
- [ ] #7 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->
