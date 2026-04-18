---
id: TASK-5
title: Add run summary on ralph.sh exit
status: To Do
assignee: []
created_date: '2026-04-18 10:18'
updated_date: '2026-04-18 12:58'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Print a plain-text run summary to stdout on every exit path (clean exit, max iterations reached, error, timeout, Ctrl+C/SIGTERM). Currently ralph.sh exits with minimal or no info about the run. A summary helps users understand what happened during overnight/autonomous runs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Summary prints to stdout on every exit path: clean completion, max iterations reached, error (on-error=stop), and interrupt (SIGINT/SIGTERM)
- [ ] #2 Summary includes: tasks completed count, total wall time, iterations used, exit reason, tasks remaining count
- [ ] #3 Exit reason is one of: 'all tasks done', 'max iterations reached', 'error', 'interrupted'
- [ ] #4 Output format is plain text (not markdown, not JSON)
- [ ] #5 Signal traps (SIGINT/SIGTERM) trigger the summary before the script exits
- [ ] #6 Summary includes: per-iteration durations (accumulated in an array during the run, each printed) and count of failed/timed-out iterations
- [ ] #7 Tests: extract print_summary() as a sourceable function. Unit tests call it directly with arguments and assert output format (no ralph.sh execution needed). Integration tests use instant-exit tool mocks (no sleep). Only the SIGINT test may use a brief sleep (1-2s max via background launch, sleep 1, kill -SIGINT, wait). Total test suite must complete in under 10 seconds
<!-- AC:END -->
