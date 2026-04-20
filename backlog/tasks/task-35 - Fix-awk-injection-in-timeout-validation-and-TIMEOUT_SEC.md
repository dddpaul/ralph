---
id: TASK-35
title: Fix awk injection in timeout validation and TIMEOUT_SEC
status: To Do
assignee: []
created_date: '2026-04-20 16:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lines 107 and 502 inject $TIMEOUT directly into awk programs. Replace with pure bash validation: use [[ regex ]] + bc for the positive check, and printf or bc for the seconds conversion. Both are in the validation section and the loop setup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Timeout validation on line 107 uses no awk — pure bash or bc
- [ ] #2 TIMEOUT_SEC calculation on line 502 uses no awk — pure bash or bc
- [ ] #3 Fractional timeouts (e.g. 0.5) still work
- [ ] #4 All existing tests pass
<!-- AC:END -->
