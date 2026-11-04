---
id: TASK-313
title: Run integrate checks in the devcontainer under a total timeout
status: To Do
assignee: []
created_date: '2026-11-04T14:54:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-312
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run integrate's configured checks where the run's tests ran: inside the devcontainer when the run used one.

The integrate call gets a total timeout. On expiry it kills both the host process group and the process tree inside the container, and reports any interrupted merge instead of resetting it.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-019.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 When the run used the devcontainer, integrate configured checks run inside it through devcontainer exec
- [ ] #2 The orchestrator gives the integrate call a total timeout that kills the host process group and the process tree it started inside the container
- [ ] #3 A test shows no check process survives inside the container after the lock is released
- [ ] #4 After a timeout the interrupted merge state is reported, not reset
- [ ] #5 ruff, pytest and bats pass
<!-- AC:END -->
