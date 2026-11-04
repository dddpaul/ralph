---
id: TASK-316
title: Guard opted-in autonomous runs against creating tasks
status: To Do
assignee: []
created_date: '2026-11-04T14:54:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-296
  - TASK-310
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Stop autonomous runs in opted-in projects from creating tasks; follow-ups go into the task's notes instead. Owner decision: the container cannot publish an ID.

A plugin guard refuses backlog task create, shared-backlog create and the ralph-handoff skill when RALPH_AUTONOMOUS=1 and ralph.sharedBacklog is true. It is exempt from the marker gate, and documented as best effort.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-022 and FR-4.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The orchestrator sets RALPH_AUTONOMOUS=1 for every run, including inside the devcontainer
- [ ] #2 A new plugin guard wired in hooks.json refuses backlog task create (also after a cd into another repo), shared-backlog.sh create and the ralph:ralph-handoff skill when RALPH_AUTONOMOUS=1 and ralph.sharedBacklog is true, exiting 2 with a record-it-in-notes message
- [ ] #3 The guard is exempt from the marker gate and localGuards and keys only on RALPH_AUTONOMOUS and ralph.sharedBacklog
- [ ] #4 Docs and the preflight describe the guard as best effort, not an absolute boundary
- [ ] #5 The template CLAUDE.md Autonomous Mode text tells the agent to record follow-ups in its notes in opted-in projects
- [ ] #6 Tests show the guard refuses in a simulated autonomous run, including with pluginHooks false or absent and the marker removed, and allows the same commands interactively and in clones that do not enforce
- [ ] #7 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
