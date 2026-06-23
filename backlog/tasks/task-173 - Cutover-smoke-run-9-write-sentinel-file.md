---
id: TASK-173
title: 'Cutover smoke run 9: write sentinel file'
status: Done
assignee: []
created_date: '2026-06-22 16:29'
updated_date: '2026-06-23 05:10'
labels:
  - cutover-smoke
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Throwaway gate-victim task for TASK-156's 5+5 clean-run cutover gate. Ralph picks this via --tasks whitelist; the task and its sentinel file are deleted in TASK-156 Phase E once cutover lands.

Instructions for ralph: Write the file tests/scripts/cutover-sentinels/run-9.txt with the single line 'Cutover smoke run 9'.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/scripts/cutover-sentinels/run-9.txt exists
- [x] #2 tests/scripts/cutover-sentinels/run-9.txt contains the literal text 'Cutover smoke run 9'
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: write tests/scripts/cutover-sentinels/run-9.txt with literal 'Cutover smoke run 9'.

Commit: `b843cd4` - task-173: Write cutover smoke sentinel file run-9.txt

Review: APPROVED by task-reviewer agent. Diff is +1 line creating run-9.txt with literal 'Cutover smoke run 9', matching run-1..run-8 shape.
<!-- SECTION:NOTES:END -->
