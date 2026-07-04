---
id: TASK-189
title: Repoint build and test configuration to new paths
status: To Do
assignee: []
created_date: '2026-07-03 09:37'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-188
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update pyproject and bats tests to the relocated paths so the suites run green. See design/ralph-marketplace-prd.md US-003.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 pyproject.toml pythonpath, testpaths, and ruff src/include/strict reference plugins/ralph/skills/ralph-run/...
- [ ] #2 bats files under tests/ reference plugins/ralph/skills/ralph-run/scripts/...
- [ ] #3 uv run pytest passes
- [ ] #4 The bats suite passes
<!-- AC:END -->
