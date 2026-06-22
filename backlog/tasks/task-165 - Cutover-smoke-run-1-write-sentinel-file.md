---
id: TASK-165
title: 'Cutover smoke run 1: write sentinel file'
status: Done
assignee: []
created_date: '2026-06-22 16:29'
updated_date: '2026-06-22 16:43'
labels:
  - cutover-smoke
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Throwaway gate-victim task for TASK-156's 5+5 clean-run cutover gate. Ralph picks this via --tasks whitelist; the task and its sentinel file are deleted in TASK-156 Phase E once cutover lands.

Instructions for ralph: Write the file tests/scripts/cutover-sentinels/run-1.txt with the single line 'Cutover smoke run 1'.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/scripts/cutover-sentinels/run-1.txt exists
- [x] #2 tests/scripts/cutover-sentinels/run-1.txt contains the literal text 'Cutover smoke run 1'
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Create tests/scripts/cutover-sentinels/run-1.txt containing the literal line 'Cutover smoke run 1'. Two ACs: file exists; file content matches.

task-reviewer APPROVED: both AC satisfied, diff scoped to exactly the two intended files (task md + sentinel), no R1-R16 violations. Sentinel file at tests/scripts/cutover-sentinels/run-1.txt contains literal 'Cutover smoke run 1' + newline.
<!-- SECTION:NOTES:END -->
