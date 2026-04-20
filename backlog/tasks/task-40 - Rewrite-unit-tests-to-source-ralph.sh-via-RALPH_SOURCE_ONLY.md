---
id: TASK-40
title: Rewrite unit tests to source ralph.sh via RALPH_SOURCE_ONLY
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 16:15'
updated_date: '2026-04-20 18:47'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Unit tests in argument-validation.bats duplicate validation logic inline instead of testing ralph.sh directly. Now that RALPH_SOURCE_ONLY=1 guard exists, tests should source ralph.sh and test actual functions/behavior. This ensures tests break when ralph.sh changes. Also update status-file.bats and run-summary.bats to source ralph.sh instead of (now removed) lib files — verify they already do after TASK-26 inlining.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 argument-validation.bats sources ralph.sh with RALPH_SOURCE_ONLY=1
- [x] #2 Tests call actual ralph.sh validation logic, not inline copies
- [x] #3 status-file.bats sources ralph.sh (not lib/status.sh)
- [x] #4 run-summary.bats sources ralph.sh (not lib/summary.sh)
- [x] #5 All tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `9de0bc1` - task-40: Rewrite argument-validation.bats to source ralph.sh via RALPH_SOURCE_ONLY

Plan: Extract arg parsing (lines 44-136) into parse_args() function, validation (lines 138-172) into validate_args() function. Both callable after RALPH_SOURCE_ONLY source. Tests call parse_args/validate_args explicitly. The RALPH_SOURCE_ONLY guard still skips execution but the functions are available.

Commit: `a68b0bd` - task-40: Extract parse_args/validate_args, rewrite argument-validation tests

Extracted parse_args() and validate_args() from inline code, tests now call actual functions. Removed duplicate dependency tests (covered by dependency-checks.bats). Files: ralph.sh, tests/unit/argument-validation.bats.
<!-- SECTION:NOTES:END -->
