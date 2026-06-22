---
id: TASK-169
title: 'Cutover smoke run 5: write sentinel file'
status: In Progress
assignee: []
created_date: '2026-06-22 16:29'
updated_date: '2026-06-22 18:52'
labels:
  - cutover-smoke
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Throwaway gate-victim task for TASK-156's 5+5 clean-run cutover gate. Ralph picks this via --tasks whitelist; the task and its sentinel file are deleted in TASK-156 Phase E once cutover lands.

Instructions for ralph: Write the file tests/scripts/cutover-sentinels/run-5.txt with the single line 'Cutover smoke run 5'.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/scripts/cutover-sentinels/run-5.txt exists
- [x] #2 tests/scripts/cutover-sentinels/run-5.txt contains the literal text 'Cutover smoke run 5'
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Create branch task-169. Write tests/scripts/cutover-sentinels/run-5.txt with line 'Cutover smoke run 5'. Verify both ACs. Run task-reviewer agent. Mark Done. Merge.
<!-- SECTION:NOTES:END -->
