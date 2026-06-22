---
id: TASK-171
title: 'Cutover smoke run 7: write sentinel file'
status: Done
assignee: []
created_date: '2026-06-22 16:29'
updated_date: '2026-06-22 20:02'
labels:
  - cutover-smoke
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Throwaway gate-victim task for TASK-156's 5+5 clean-run cutover gate. Ralph picks this via --tasks whitelist; the task and its sentinel file are deleted in TASK-156 Phase E once cutover lands.

Instructions for ralph: Write the file tests/scripts/cutover-sentinels/run-7.txt with the single line 'Cutover smoke run 7'.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/scripts/cutover-sentinels/run-7.txt exists
- [x] #2 tests/scripts/cutover-sentinels/run-7.txt contains the literal text 'Cutover smoke run 7'
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Write the sentinel file tests/scripts/cutover-sentinels/run-7.txt with the single line 'Cutover smoke run 7'. Check off both AC items. This is part of the TASK-156 cutover gate (Phase D run 7).

Commit: `390c594` - task-171: Write cutover smoke sentinel file run-7.txt

Implemented: created tests/scripts/cutover-sentinels/run-7.txt with literal 'Cutover smoke run 7'. Ruff: clean. Pytest: 201 passed. task-reviewer: APPROVED. Commit: 390c594.
<!-- SECTION:NOTES:END -->
