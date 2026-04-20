---
id: TASK-26
title: Inline lib files into ralph.sh for single-file distribution
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 12:14'
updated_date: '2026-04-20 13:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Move functions from lib/status.sh and lib/summary.sh back into ralph.sh so the script is distributable as a single file. Add a RALPH_SOURCE_ONLY guard so unit tests can source ralph.sh without triggering execution. Update the 2 unit tests to source ralph.sh instead of lib files. Delete lib/ directory.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All functions from lib/status.sh and lib/summary.sh are defined inside ralph.sh
- [x] #2 lib/ directory is removed
- [x] #3 ralph.sh has a RALPH_SOURCE_ONLY guard that prevents execution when sourced by tests
- [x] #4 Unit tests source ralph.sh instead of lib files and pass
- [x] #5 Integration and e2e tests pass without changes
- [x] #6 All tests pass with no increase in test runtime
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
All work was already committed in 3b9c3db on master. Functions inlined at ralph.sh:123-241, RALPH_SOURCE_ONLY guard at :244-247, lib/ deleted. All 54 unit tests and 60 integration tests pass.
<!-- SECTION:NOTES:END -->
