---
id: TASK-159
title: Match bash exit code on max-iterations w/ no completions or failed iterations
status: To Do
assignee: []
created_date: '2026-06-21 20:25'
labels:
  - 'feature:ralph-python-refactor'
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Python orchestrator's run() always returns 0 on 'max iterations reached' exit path; bash exits 1 when TASKS_COMPLETED==0 || FAILED_ITERATIONS>0 (ralph.sh:889-894). US-005 AC #7 pins the closed-set exit_reason but not the exit code — file as a parity gap to close before US-007 cutover.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 When loop ends with exit_reason='max iterations reached', returns 1 if tasks_completed==0 OR failed_iterations>0
- [ ] #2 Otherwise returns 0
- [ ] #3 Test: synthetic run with 0 completions returns 1
- [ ] #4 Test: synthetic run with 1 completion + 1 failure returns 1
- [ ] #5 Test: synthetic run with 1+ completions and 0 failures returns 0
<!-- AC:END -->
