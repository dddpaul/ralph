---
id: TASK-42
title: Calculate elapsed time from started_at in ralph-status skill
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 16:19'
updated_date: '2026-04-20 19:19'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-status reads the elapsed field from .ralph-status.json, but this field is stale (only updated at iteration boundaries). For running state, the skill should calculate elapsed as now - started_at instead. For completed/failed states, keep using the elapsed field from the file since it was written at exit time.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 When state is running, elapsed is calculated as current time minus started_at
- [x] #2 When state is completed or failed, elapsed uses the value from the status file
- [x] #3 Elapsed displays correctly when checked mid-iteration
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Modify ralph-status skill.md Step 1 to add instruction: when state is 'running', calculate elapsed as (current_epoch - started_at_epoch) instead of using the elapsed field from JSON. For completed/failed states, keep using the file's elapsed value. Add a note in Step 3 referencing this computed value.

Implemented: Added 'Compute live elapsed time' subsection to ralph-status skill (Step 1). When state=running, elapsed is calculated as current_epoch - started_at_epoch. For completed/failed, uses file value as-is. File changed: ~/.claude/skills/ralph-status/skill.md (outside repo).
<!-- SECTION:NOTES:END -->
