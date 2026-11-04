---
id: TASK-314
title: Teach the Ralph task picker to skip tasks held by someone else
status: In Progress
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-04T19:08:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Teach Ralph's task picker about assignees: parse Assignee from backlog task view --plain, and skip To Do tasks held by someone other than the holder. A bare @claude counts as unassigned.

The template CLAUDE.md Autonomous Mode text states the same rule.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-020 and FR-6.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 BacklogTask in `plugins/ralph/skills/ralph-run/scripts/ralph/tasks.py` parses Assignee from backlog task view --plain, including several assignees
- [x] #2 In every project, default mode skips To Do tasks with an assignee other than the holder, and a bare @claude counts as unassigned
- [x] #3 The template CLAUDE.md Autonomous Mode selection text states the same assignee rule
- [x] #4 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: parse Assignee into BacklogTask.assignees; held_by_other() skips candidates with an assignee besides the holder and bare @claude; resolve_holder() reads SHARED_BACKLOG_HOLDER then git config ralph.holder (--as stays a shared-backlog.sh flag); loop resolves it once per run; update the Autonomous Mode selection line in live + template CLAUDE.md; tests in tests/python/test_task_picker_assignees.py.
<!-- SECTION:NOTES:END -->
