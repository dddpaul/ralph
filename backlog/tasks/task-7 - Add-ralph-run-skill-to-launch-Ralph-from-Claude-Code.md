---
id: TASK-7
title: Add ralph-run skill to launch Ralph from Claude Code
status: To Do
assignee: []
created_date: '2026-04-18 12:01'
updated_date: '2026-04-18 12:11'
labels: []
dependencies:
  - TASK-6
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A Claude Code skill (/ralph-run) that launches ralph.sh in the background from an interactive Claude Code session. Handles nohup/disown for full process detachment so Ralph survives session exit. Validates preconditions before launching: To Do tasks exist, devcontainer CLI available, Ralph not already running (check PID in status file). Reports PID and confirms launch. Depends on TASK-6 (status file must exist for already-running detection).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Skill file created at skills/ralph-run/SKILL.md
- [ ] #2 Launches ralph.sh with nohup/disown, fully detached from parent session
- [ ] #3 Reports PID and confirms launch to user after successful start
- [ ] #4 Validates preconditions: To Do tasks exist in backlog, no Ralph already running (checks PID from backlog/.ralph-status.json and verifies process is alive). Devcontainer CLI check only when --devcontainer is used
- [ ] #5 Locates ralph.sh by checking ./ralph.sh first, then scripts/ralph/ralph.sh. Errors if not found
- [ ] #6 Default arguments match typical ralph loop invocation: tool=claude, effort=max, timeout=60, devcontainer=true, max_iterations=10. All overridable via skill arguments
<!-- AC:END -->
