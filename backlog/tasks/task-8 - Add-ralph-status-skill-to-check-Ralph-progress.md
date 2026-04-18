---
id: TASK-8
title: Add ralph-status skill to check Ralph progress
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
A Claude Code skill (/ralph-status) that reads backlog/.ralph-status.json and backlog task list to present a concise progress summary. Designed for quick checking from mobile via Happy app. Depends on TASK-6 (status file format).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Skill file created at skills/ralph-status/SKILL.md
- [ ] #2 Reads backlog/.ralph-status.json and formats a concise human-readable summary with: state, iteration progress, elapsed time, current task, done tasks, remaining count, errors
- [ ] #3 Falls back gracefully when no status file exists (Ralph not running or never ran)
- [ ] #4 Includes tail of backlog/.ralph-run.log (last 10 lines) if user asks for details
- [ ] #5 If state is running, verify PID is alive. If process is dead, report Ralph appears to have crashed (PID not found) instead of showing running state
<!-- AC:END -->
