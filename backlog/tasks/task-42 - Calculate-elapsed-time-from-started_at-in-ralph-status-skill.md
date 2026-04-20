---
id: TASK-42
title: Calculate elapsed time from started_at in ralph-status skill
status: To Do
assignee: []
created_date: '2026-04-20 16:19'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-status reads the elapsed field from .ralph-status.json, but this field is stale (only updated at iteration boundaries). For running state, the skill should calculate elapsed as now - started_at instead. For completed/failed states, keep using the elapsed field from the file since it was written at exit time.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 When state is running, elapsed is calculated as current time minus started_at
- [ ] #2 When state is completed or failed, elapsed uses the value from the status file
- [ ] #3 Elapsed displays correctly when checked mid-iteration
<!-- AC:END -->
