---
id: TASK-13
title: Fix current_task tracking in ralph.sh status file
status: To Do
assignee: []
created_date: '2026-04-18 19:11'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
current_task in backlog/.ralph-status.json is always empty because _get_current_task() queries 'In Progress' tasks at line 325 before the AI agent moves the task from 'To Do'. Fix: derive CURRENT_TASK from TODO_OUTPUT (already available at line 316) by extracting the first TASK-* ID. Remove the now-unused _get_current_task() function (lines 158-160). Update status-file-integration.bats test 'current_task populated from In Progress tasks' to mock a To Do task instead.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CURRENT_TASK is derived from TODO_OUTPUT via grep -o TASK-[0-9]* | head -1 at line 325
- [ ] #2 _get_current_task function (lines 158-160) is removed
- [ ] #3 status-file-integration.bats test 'current_task populated from In Progress tasks' updated to verify current_task from To Do list
- [ ] #4 All integration tests pass
- [ ] #5 All unit tests pass
<!-- AC:END -->
