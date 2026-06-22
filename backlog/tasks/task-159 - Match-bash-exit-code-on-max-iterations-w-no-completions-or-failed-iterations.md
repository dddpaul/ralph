---
id: TASK-159
title: Match bash exit code on max-iterations w/ no completions or failed iterations
status: Done
assignee:
  - Claude
created_date: '2026-06-21 20:25'
updated_date: '2026-06-22 05:54'
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
- [x] #1 When loop ends with exit_reason='max iterations reached', returns 1 if tasks_completed==0 OR failed_iterations>0
- [x] #2 Otherwise returns 0
- [x] #3 Test: synthetic run with 0 completions returns 1
- [x] #4 Test: synthetic run with 1 completion + 1 failure returns 1
- [x] #5 Test: synthetic run with 1+ completions and 0 failures returns 0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
- Modify loop._run_loop: at fall-through (max iterations reached), set state.exit_code=1 if tasks_completed==0 OR failed_iterations>0; leave 0 otherwise (matches ralph.sh:889-894).
- Add test_loop_exit_code.py with 3 synthetic scenarios via stubbed Tool + monkeypatched tasks_module:
  (a) 0 completions, 0 failures -> exit 1 (AC #3)
  (b) 1 completion + 1 failure -> exit 1 (AC #4)
  (c) 1+ completion(s), 0 failures -> exit 0 (AC #5)
- Run uv run pytest and uv run ruff check .

Implemented loop._run_loop fall-through: state.exit_code=1 when tasks_completed==0 OR failed_iterations>0 (matches ralph.sh:889-894). Added test_loop_exit_code.py covering AC #3-5. uv run pytest: 181 passed. uv run ruff check .: clean. task-reviewer: APPROVED (cosmetic docstring nit applied).
<!-- SECTION:NOTES:END -->
