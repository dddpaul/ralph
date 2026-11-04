---
id: TASK-314
title: Teach the Ralph task picker to skip tasks held by someone else
status: To Do
assignee: []
created_date: '2026-11-04T14:54:00Z'
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
- [ ] #1 BacklogTask in `plugins/ralph/skills/ralph-run/scripts/ralph/tasks.py` parses Assignee from backlog task view --plain, including several assignees
- [ ] #2 In every project, default mode skips To Do tasks with an assignee other than the holder, and a bare @claude counts as unassigned
- [ ] #3 The template CLAUDE.md Autonomous Mode selection text states the same assignee rule
- [ ] #4 ruff, pytest and bats pass
<!-- AC:END -->
