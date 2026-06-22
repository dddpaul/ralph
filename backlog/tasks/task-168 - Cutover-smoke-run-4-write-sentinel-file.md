---
id: TASK-168
title: 'Cutover smoke run 4: write sentinel file'
status: Done
assignee: []
created_date: '2026-06-22 16:29'
updated_date: '2026-06-22 18:29'
labels:
  - cutover-smoke
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Throwaway gate-victim task for TASK-156's 5+5 clean-run cutover gate. Ralph picks this via --tasks whitelist; the task and its sentinel file are deleted in TASK-156 Phase E once cutover lands.

Instructions for ralph: Write the file tests/scripts/cutover-sentinels/run-4.txt with the single line 'Cutover smoke run 4'.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/scripts/cutover-sentinels/run-4.txt exists
- [x] #2 tests/scripts/cutover-sentinels/run-4.txt contains the literal text 'Cutover smoke run 4'
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Write tests/scripts/cutover-sentinels/run-4.txt containing the line 'Cutover smoke run 4' on branch task-168; verify AC1+AC2; review via task-reviewer; merge to master.

Commit: `8e3a4bb` - task-168: Write cutover smoke sentinel file run-4.txt

Implemented per AC: wrote tests/scripts/cutover-sentinels/run-4.txt with the single line 'Cutover smoke run 4'. AC1+AC2 verified. task-reviewer agent verdict: APPROVED (8-item checklist + R1–R16 all PASS/N-A). Commit: 8e3a4bb.
<!-- SECTION:NOTES:END -->
