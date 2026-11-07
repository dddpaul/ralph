---
id: TASK-313
title: Run integrate checks in the devcontainer under a total timeout
status: Done
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-07T15:17:00Z'
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
- [x] #1 When the run used the devcontainer, integrate configured checks run inside it through devcontainer exec
- [x] #2 The orchestrator gives the integrate call a total timeout that kills the host process group and the process tree it started inside the container
- [x] #3 A test shows no check process survives inside the container after the lock is released
- [x] #4 After a timeout the interrupted merge state is reported, not reset
- [x] #5 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: push.integrate gets devcontainer + total timeout (RALPH_INTEGRATE_TIMEOUT, default 1800s). New ralph/checks_context.py: SHARED_BACKLOG_CHECKS_EXEC = devcontainer exec --workspace-folder <root> --remote-env RALPH_INTEGRATE_TAG=<token>; the tag finds the in-container process tree, which a reaper (devcontainer exec sh -c, /proc environ scan, SIGKILL) stops. shared-backlog.sh runs SHARED_BACKLOG_CHECKS_KILL after its deadline or a signal, before the lock is released; the orchestrator, on its timeout, SIGTERMs the script group, SIGKILLs every group under it after a grace, reaps the container again, and reports local_state (merge in progress) without reset. Loop passes args.devcontainer.

Commit: `8d13bf9` - task-313: run integrate checks in the devcontainer under a total timeout

Commit: `0d56bd8` - task-313: pass the devcontainer exec prefix unquoted and SIGKILL only live process groups

Review: APPROVED 0d56bd88b1ed421eb8b907e06802666805f686f0

Follow-up: verify on a host with a real devcontainer: run integrate with hanging checks (e.g. checks 'sleep 600') and RALPH_INTEGRATE_TIMEOUT=60 from a --devcontainer run; confirm no process tagged RALPH_INTEGRATE_TAG survives in the container (docker exec <id> sh -c 'grep -l RALPH_INTEGRATE_TAG /proc/[0-9]*/environ'). Tests here use a fake devcontainer that detaches the container side like docker exec.

Done: integrate's checks run in the devcontainer through devcontainer exec with a tag on the process tree; push.integrate has a total timeout (RALPH_INTEGRATE_TIMEOUT, default 1800s, script deadline 30s earlier) that kills the script's process groups, reaps the tagged container tree (also done by shared-backlog.sh via SHARED_BACKLOG_CHECKS_KILL before it releases the lock) and reports local_state without reset. pytest 1476 passed/4 skipped, bats 283 ok, shell suites 0 failures, ruff at master baseline (ruff 0.14.0 clean).

Commit: `bd401f9` - task-313: bump plugin version to 0.24.0 (minor)
<!-- SECTION:NOTES:END -->
