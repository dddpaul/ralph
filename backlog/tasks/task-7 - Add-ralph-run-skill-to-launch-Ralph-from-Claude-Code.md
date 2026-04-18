---
id: TASK-7
title: Add ralph-run skill to launch Ralph from Claude Code
status: Done
assignee:
  - '@claude'
created_date: '2026-04-18 12:01'
updated_date: '2026-04-18 14:13'
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
- [x] #1 Skill file created at skills/ralph-run/SKILL.md
- [x] #2 Launches ralph.sh with nohup/disown, fully detached from parent session
- [x] #3 Reports PID and confirms launch to user after successful start
- [x] #4 Validates preconditions: To Do tasks exist in backlog, no Ralph already running (checks PID from backlog/.ralph-status.json and verifies process is alive). Devcontainer CLI check only when --devcontainer is used
- [x] #5 Locates ralph.sh by checking ./ralph.sh first, then scripts/ralph/ralph.sh. Errors if not found
- [x] #6 Default arguments match typical ralph loop invocation: tool=claude, effort=max, timeout=60, devcontainer=true, max_iterations=10. All overridable via skill arguments
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Create skills/ralph-run/SKILL.md skill file. The skill will: (1) locate ralph.sh (./ralph.sh then scripts/ralph/ralph.sh), (2) check preconditions (To Do tasks exist, no running Ralph via backlog/.ralph-status.json PID check), (3) launch ralph.sh with nohup/disown for full detachment, (4) report PID. Default args: --tool claude --effort max --timeout 60 --devcontainer --max_iterations 10, all overridable via skill args.

Commit: `73693ab` - task-7: Ralph-run skill to launch ralph.sh from Claude Code

Implemented ralph-run skill at skills/ralph-run/SKILL.md. Skill launches ralph.sh via nohup/disown for full process detachment. Validates preconditions (To Do tasks exist, no running Ralph via PID check, devcontainer CLI when needed). Defaults: tool=claude, effort=max, timeout=60, devcontainer=true, max_iterations=10. All overridable via skill args.
<!-- SECTION:NOTES:END -->
