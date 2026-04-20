---
id: TASK-26
title: Inline lib files into ralph.sh for single-file distribution
status: To Do
assignee:
  - '@claude'
created_date: '2026-04-20 12:14'
updated_date: '2026-04-20 12:20'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Move functions from lib/status.sh and lib/summary.sh back into ralph.sh so the script is distributable as a single file. Add a RALPH_SOURCE_ONLY guard so unit tests can source ralph.sh without triggering execution. Update the 2 unit tests to source ralph.sh instead of lib files. Delete lib/ directory.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All functions from lib/status.sh and lib/summary.sh are defined inside ralph.sh
- [ ] #2 lib/ directory is removed
- [ ] #3 ralph.sh has a RALPH_SOURCE_ONLY guard that prevents execution when sourced by tests
- [ ] #4 Unit tests source ralph.sh instead of lib files and pass
- [ ] #5 Integration and e2e tests pass without changes
- [ ] #6 All tests pass with no increase in test runtime
<!-- AC:END -->
