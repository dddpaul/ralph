---
id: TASK-315
title: Claim and push a task before every Ralph iteration in enforcing clones
status: To Do
assignee: []
created_date: '2026-11-04T14:54:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-306
  - TASK-310
  - TASK-312
  - TASK-314
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In enforcing clones, every Ralph run claims a task and pushes the claim before working on it. That covers default mode and tasks=N alike.

Run lock:
- The run takes the run lock for its whole duration.
- It passes RALPH_RUN_LOCK_TOKEN to its own protocol calls, inside the devcontainer too.

Holder:
- It is resolved once per run and passed into the container.

Claims:
- tasks=N refuses a task another holder holds unless --force-claim is given.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-021 and FR-6, FR-7.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 In an enforcing clone the orchestrator holds the run lock for the whole run and passes RALPH_RUN_LOCK_TOKEN to its own protocol calls, including inside the devcontainer
- [ ] #2 A second run, and an unrelated sync or claim in the same clone, refuse while the run lock is held (tested)
- [ ] #3 The holder is resolved once per run and passed into the devcontainer as SHARED_BACKLOG_HOLDER, and a missing holder refuses the run in an enforcing clone
- [ ] #4 Default mode syncs, picks the lowest eligible task, claims it, pushes the claim and re-checks it before the iteration starts, trying the next candidate when the claim loses
- [ ] #5 tasks=N claims, pushes and re-checks the same way, and refuses a task held by another holder unless --force-claim is given
- [ ] #6 A claim already held by this holder is accepted after the status and dependency checks
- [ ] #7 Tests cover two pickers in two clones racing for one task with exactly one claim landing, a missing holder, several assignees, an already-held claim and the delegated holder inside the container
- [ ] #8 ruff, pytest and bats pass
<!-- AC:END -->
