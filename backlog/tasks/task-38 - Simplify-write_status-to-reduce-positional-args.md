---
id: TASK-38
title: Simplify write_status to reduce positional args
status: To Do
assignee: []
created_date: '2026-04-20 16:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
write_status takes 15 positional args (lines 170-185) which is hard to read and extend. Refactor: move JSON construction into _update_status directly since it's the only caller, using the module-level variables (STATUS_FILE, CURRENT_ITERATION, etc.) instead of passing them. write_status can be removed or reduced to a thin wrapper. Keep _status_json_escape and _status_json_array as helpers.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 write_status no longer takes 15 positional arguments
- [ ] #2 _update_status builds and writes JSON directly using module-level state
- [ ] #3 Status JSON output is identical to before (same fields, same format)
- [ ] #4 Unit tests for status file still pass
- [ ] #5 Integration tests for status file still pass
<!-- AC:END -->
