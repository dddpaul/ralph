---
id: TASK-173
title: 'Cutover smoke run 9: write sentinel file'
status: To Do
assignee: []
created_date: '2026-06-22 16:29'
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
- [ ] #1 tests/scripts/cutover-sentinels/run-9.txt exists
- [ ] #2 tests/scripts/cutover-sentinels/run-9.txt contains the literal text 'Cutover smoke run 9'
<!-- AC:END -->
