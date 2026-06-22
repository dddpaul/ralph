---
id: TASK-170
title: 'Cutover smoke run 6: write sentinel file'
status: Done
assignee: []
created_date: '2026-06-22 16:29'
updated_date: '2026-06-22 19:49'
labels:
  - cutover-smoke
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Throwaway gate-victim task for TASK-156's 5+5 clean-run cutover gate. Ralph picks this via --tasks whitelist; the task and its sentinel file are deleted in TASK-156 Phase E once cutover lands.

Instructions for ralph: Write the file tests/scripts/cutover-sentinels/run-6.txt with the single line 'Cutover smoke run 6'.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/scripts/cutover-sentinels/run-6.txt exists
- [x] #2 tests/scripts/cutover-sentinels/run-6.txt contains the literal text 'Cutover smoke run 6'
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Create tests/scripts/cutover-sentinels/run-6.txt with the literal text 'Cutover smoke run 6'. Mirror prior run-N sentinel format.

Commit: `ee73896` - task-170: Write cutover smoke sentinel file run-6.txt

task-reviewer APPROVED. Sentinel file run-6.txt created with literal 'Cutover smoke run 6'.
<!-- SECTION:NOTES:END -->
