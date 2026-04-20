---
id: TASK-40
title: Rewrite unit tests to source ralph.sh via RALPH_SOURCE_ONLY
status: To Do
assignee: []
created_date: '2026-04-20 16:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Unit tests in argument-validation.bats duplicate validation logic inline instead of testing ralph.sh directly. Now that RALPH_SOURCE_ONLY=1 guard exists, tests should source ralph.sh and test actual functions/behavior. This ensures tests break when ralph.sh changes. Also update status-file.bats and run-summary.bats to source ralph.sh instead of (now removed) lib files — verify they already do after TASK-26 inlining.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 argument-validation.bats sources ralph.sh with RALPH_SOURCE_ONLY=1
- [ ] #2 Tests call actual ralph.sh validation logic, not inline copies
- [ ] #3 status-file.bats sources ralph.sh (not lib/status.sh)
- [ ] #4 run-summary.bats sources ralph.sh (not lib/summary.sh)
- [ ] #5 All tests pass
<!-- AC:END -->
