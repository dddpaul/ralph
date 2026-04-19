---
id: TASK-13
title: Fix current_task tracking in ralph.sh status file
status: Done
assignee:
  - '@claude'
created_date: '2026-04-18 19:11'
updated_date: '2026-04-19 07:23'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
current_task in backlog/.ralph-status.json is always empty because _get_current_task() queries 'In Progress' tasks at line 325 before the AI agent moves the task from 'To Do'. Fix: derive CURRENT_TASK from TODO_OUTPUT (already available at line 316) by extracting the first TASK-* ID. Remove the now-unused _get_current_task() function (lines 158-160). Update status-file-integration.bats test 'current_task populated from In Progress tasks' to mock a To Do task instead.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CURRENT_TASK is derived from TODO_OUTPUT via grep -o TASK-[0-9]* | head -1 at line 325
- [x] #2 _get_current_task function (lines 158-160) is removed
- [x] #3 status-file-integration.bats test 'current_task populated from In Progress tasks' updated to verify current_task from To Do list
- [x] #4 All integration tests pass
- [x] #5 All unit tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) In ralph.sh line 325, replace CURRENT_TASK=$(_get_current_task) with CURRENT_TASK=$(echo "$TODO_OUTPUT" | grep -o 'TASK-[0-9]*' | head -1). (2) Remove _get_current_task function (lines 158-160). (3) Update test at line 149 to verify current_task is derived from To Do list — mock a To Do task and verify status file has the task ID. No In Progress mock needed.

Commit: `6a1fe9e` - task-13: Derive current_task from To Do list instead of In Progress query

Implemented: Removed _get_current_task() function, replaced CURRENT_TASK assignment at line 322 with extraction from TODO_OUTPUT. Updated integration test to verify current_task from To Do list with actual value assertion. Files changed: ralph.sh, tests/integration/status-file-integration.bats.
<!-- SECTION:NOTES:END -->
