---
id: TASK-5
title: Add run summary on ralph.sh exit
status: Done
assignee:
  - '@claude'
created_date: '2026-04-18 10:18'
updated_date: '2026-04-18 13:43'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Print a plain-text run summary to stdout on every exit path (clean exit, max iterations reached, error, timeout, Ctrl+C/SIGTERM). Currently ralph.sh exits with minimal or no info about the run. A summary helps users understand what happened during overnight/autonomous runs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Summary prints to stdout on every exit path: clean completion, max iterations reached, error (on-error=stop), and interrupt (SIGINT/SIGTERM)
- [x] #2 Summary includes: tasks completed count, total wall time, iterations used, exit reason, tasks remaining count
- [x] #3 Exit reason is one of: 'all tasks done', 'max iterations reached', 'error', 'interrupted'
- [x] #4 Output format is plain text (not markdown, not JSON)
- [x] #5 Signal traps (SIGINT/SIGTERM) trigger the summary before the script exits
- [x] #6 Summary includes: per-iteration durations (accumulated in an array during the run, each printed) and count of failed/timed-out iterations
- [x] #7 Tests: extract print_summary() as a sourceable function. Unit tests call it directly with arguments and assert output format (no ralph.sh execution needed). Integration tests use instant-exit tool mocks (no sleep). Only the SIGINT test may use a brief sleep (1-2s max via background launch, sleep 1, kill -SIGINT, wait). Total test suite must complete in under 10 seconds
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Extract print_summary() into a sourceable file (lib/summary.sh). (2) Track state: TASKS_COMPLETED, FAILED_ITERATIONS, ITER_DURATIONS array, EXIT_REASON, RUN_START_TIME. (3) Call print_summary on every exit: clean completion (all tasks done), max iterations, error (on-error=stop), SIGINT/SIGTERM traps. (4) Output format: plain text with fields from AC#2 and AC#6. (5) Write unit tests calling print_summary directly with args. (6) Write integration tests with mock tools for each exit path. (7) SIGINT test uses background+kill approach with 1-2s sleep.

Commit: `79d9d60` - task-5: Print run summary on every ralph.sh exit path

Implemented run summary in lib/summary.sh. Summary prints on all exit paths: clean completion, max iterations, error, and SIGINT/SIGTERM. Changed set -eo pipefail to set -o pipefail to fix error handling. Added 18 new tests (11 unit + 7 integration). Updated 2 existing test files for new output format.
<!-- SECTION:NOTES:END -->
