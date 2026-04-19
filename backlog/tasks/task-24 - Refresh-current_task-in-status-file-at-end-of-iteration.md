---
id: TASK-24
title: Refresh current_task in status file at end of iteration
status: Done
assignee:
  - '@claude'
created_date: '2026-04-19 10:20'
updated_date: '2026-04-19 19:17'
labels: []
dependencies:
  - TASK-13
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-13 fixes current_task tracking by deriving it from TODO_OUTPUT before the iteration runs (line 321). But TODO_OUTPUT is captured at iteration start, so 'current_task' in the status file becomes stale immediately after the agent moves the task to In Progress or Done.

Fix: at the end of each iteration (after line 397, ITER_ELAPSED computation), re-query 'backlog task list -s "In Progress" --plain' to get the actual current task. If empty, set current_task to null. Update status file via _update_status.

This is a follow-up to TASK-13, depends on it being merged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 After each iteration completes, status file current_task reflects In Progress task (or null if none)
- [x] #2 Test added in tests/integration/status-file-integration.bats verifying current_task updates after iteration
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Brainstorm Design (2026-04-19)

Tight scope: single-line change in ralph.sh + 2 new integration tests.

## Change to ralph.sh

After line 399 (LAST_ITER_DURATION assignment), add one line:

```bash
ITER_ELAPSED=$(( $(date +%s) - ITER_START ))
ITER_DURATIONS+=("$ITER_ELAPSED")
LAST_ITER_DURATION="$ITER_ELAPSED"

# NEW: refresh current_task from In Progress list
CURRENT_TASK=$(backlog task list -s 'In Progress' --plain 2>/dev/null | grep -o 'TASK-[0-9]*' | head -1)
```

All subsequent `_update_status` calls (ITER_FAILED branch at line 420, success branch at line 427) will use the refreshed value.

## Semantics after refresh

- Agent completed task cleanly → task moved to Done → In Progress empty → current_task = '' (null in JSON)
- Agent left task In Progress → current_task = 'TASK-XX'
- Agent picked multiple tasks (violates TASK-18 rule) → first In Progress via head -1

## Test additions (tests/integration/status-file-integration.bats)

Test 1 — clean completion clears current_task:
```bash
@test 'status file current_task is null after iteration if no In Progress task remains' {
  setup_test_dir
  mock_backlog_multi 'TASK-5 - Test task' 'TASK-5 - Test task' 'No tasks found'
  # arg 1: To Do list (used at start)
  # arg 2: Done list (after agent completes task)
  # arg 3: In Progress list (empty after refresh)
  mock_tool 'claude' '## Task Summary'
  run "$RALPH_SCRIPT" --tool claude 1 --log-file /dev/null
  python3 -c "import json; d=json.load(open('$RALPH_STATUS_FILE')); assert d['current_task'] in (None, ''), d"
}
```

Test 2 — incomplete task stays in current_task:
```bash
@test 'status file current_task reflects In Progress task after iteration' {
  setup_test_dir
  mock_backlog_multi 'TASK-5 - Test task' 'No tasks found' 'TASK-5 - In progress'
  mock_tool 'claude' 'WIP'
  run "$RALPH_SCRIPT" --tool claude 1 --log-file /dev/null
  python3 -c "import json; d=json.load(open('$RALPH_STATUS_FILE')); assert d['current_task'] == 'TASK-5', d"
}
```

## No helper needed

Kept inline — the query is used in exactly one place and extracting a helper adds no clarity. If a future caller needs the same pattern, refactor then.

## Scope

- Modifies: ralph.sh (+1 line), tests/integration/status-file-integration.bats (+2 tests)
- Does NOT modify: existing current_task logic at line 321 (kept — it's still correct for pre-iteration state)
- No helper function, no new test fixtures, no changes to mock_backlog_multi

Plan: Add CURRENT_TASK refresh after LAST_ITER_DURATION at line 424. Add 2 integration tests verifying current_task after iteration.

Commit: `3a8d5b7` - task-24: Refresh current_task in status file after each iteration

Implemented: single-line refresh of CURRENT_TASK after iteration via backlog In Progress query. Updated test 11 to provide In Progress mock response. Added 2 new tests. All 18 status-file tests pass.
<!-- SECTION:NOTES:END -->
