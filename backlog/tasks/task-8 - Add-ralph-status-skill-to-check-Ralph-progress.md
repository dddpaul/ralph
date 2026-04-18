---
id: TASK-8
title: Add ralph-status skill to check Ralph progress
status: Done
assignee:
  - '@claude'
created_date: '2026-04-18 12:01'
updated_date: '2026-04-18 14:23'
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
- [x] #1 Skill file created at skills/ralph-status/SKILL.md
- [x] #2 Reads backlog/.ralph-status.json and formats a concise human-readable summary with: state, iteration progress, elapsed time, current task, done tasks, remaining count, errors
- [x] #3 Falls back gracefully when no status file exists (Ralph not running or never ran)
- [x] #4 Includes tail of backlog/.ralph-run.log (last 10 lines) if user asks for details
- [x] #5 If state is running, verify PID is alive. If process is dead, report Ralph appears to have crashed (PID not found) instead of showing running state
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Create skills/ralph-status/SKILL.md following existing skill pattern. The skill reads backlog/.ralph-status.json, parses fields, verifies PID when state=running, formats concise summary. Falls back gracefully when no status file. Includes log tail on request.

Commit: `51b95da` - task-8: Ralph status skill for checking autonomous agent progress

Implemented ralph-status skill. Single SKILL.md file with 6-step instructions: read status JSON, verify PID for running state, format summary, show errors, optional log tail, backlog snapshot. Follows existing skill patterns.
<!-- SECTION:NOTES:END -->
