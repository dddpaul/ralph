---
id: TASK-6
title: Add run status file to ralph.sh
status: To Do
assignee: []
created_date: '2026-04-18 11:56'
updated_date: '2026-04-18 12:14'
labels: []
dependencies:
  - TASK-5
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph.sh should always write a JSON status file (backlog/.ralph-status.json) that tracks progress of the current run. This enables checking Ralph progress from a separate Claude Code session (e.g. via Happy mobile app). The status file is written at every lifecycle point: loop start, iteration start, iteration end, completion, failure, and max-iterations reached. The log file also goes to backlog/.ralph-run.log. Both files are .gitignore'd. Use printf with proper escaping for JSON string values (escape quotes, backslashes, newlines). If jq is available, prefer it for safe JSON generation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Status file written at loop start (state=running), each iteration start (current_task updated), each iteration end (tasks_done updated, last_iteration_duration), loop exit on completion (state=completed), loop exit on failure (state=failed), loop exit on max-iterations (state=failed)
- [ ] #2 backlog/.ralph-status.json and backlog/.ralph-run.log added to .gitignore
- [ ] #3 No new CLI flags - status writing is always on
- [ ] #4 All existing tests still pass
- [ ] #5 write_status() function writes JSON with: pid, started_at, state (running/completed/failed), iteration, max_iterations, tool, tasks_done (task IDs that transitioned to Done during this run, determined by diffing backlog status before and after each iteration), tasks_remaining count, current_task (determined by running backlog task list -s "In Progress" --plain at iteration start), last_iteration_duration, elapsed, errors array, completed_at, exit_code
- [ ] #6 Full stdout/stderr is always tee'd to backlog/.ralph-run.log. The existing --log-file flag for error-only logging remains unchanged and independent
- [ ] #7 New tests verify: write_status() produces valid JSON, status file is created at loop start, status transitions through running/completed/failed states, tasks_done is populated correctly after iterations, current_task reflects In Progress task
<!-- AC:END -->
