---
id: TASK-38
title: Simplify write_status to reduce positional args
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 16:15'
updated_date: '2026-04-20 18:02'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
write_status takes 15 positional args (lines 170-185) which is hard to read and extend. Refactor: move JSON construction into _update_status directly since it's the only caller, using the module-level variables (STATUS_FILE, CURRENT_ITERATION, etc.) instead of passing them. write_status can be removed or reduced to a thin wrapper. Keep _status_json_escape and _status_json_array as helpers.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 write_status no longer takes 15 positional arguments
- [x] #2 _update_status builds and writes JSON directly using module-level state
- [x] #3 Status JSON output is identical to before (same fields, same format)
- [x] #4 Unit tests for status file still pass
- [x] #5 Integration tests for status file still pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Inline the JSON construction from write_status into _update_status, which reads module-level vars directly. (2) Remove write_status entirely — _update_status becomes the only writer. (3) Keep _status_json_escape and _status_json_array as helpers. (4) Update unit tests to set module-level vars and call _update_status instead of write_status with 15 args. (5) Run all tests to verify identical JSON output.

Commit: `647ac9f` - task-38: Inline write_status into _update_status using module-level vars

Removed write_status (15 positional args). JSON construction inlined into _update_status which reads module-level vars directly. Moved _update_status and count_remaining_tasks above RALPH_SOURCE_ONLY guard for testability. Unit tests updated to set module-level vars and mock count_remaining_tasks.
<!-- SECTION:NOTES:END -->
