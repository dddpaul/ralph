---
id: TASK-164
title: Honor --tasks whitelist in tasks_remaining recompute between iterations
status: In Progress
assignee: []
created_date: '2026-06-22 10:14'
updated_date: '2026-06-22 10:36'
labels:
  - 'feature:ralph-python-refactor'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph/loop.py:319 (_update_after_iteration) calls tasks_module.count_remaining() WITHOUT the whitelist argument when recomputing tasks_remaining at end of iteration. The start-of-iteration write at loop.py:213 does pass whitelist correctly, and the run summary at loop.py:350 uses the whitelist-aware value. But the between-iteration JSON snapshot has the wrong tasks_remaining — reflects the whole To Do queue instead of the whitelisted subset.

Bash honors the whitelist throughout (ralph.sh:347-367 + count_remaining_tasks callsite). This is a real bug in the JSON contract, not just a text deviation — observable by any reader of .ralph-status.json (status skill, monitor, downstream tooling) between iterations of a whitelisted run. Symptom: tasks_remaining flickers between correct (during iteration) and inflated (between iterations).

Fix: pass the whitelist argument through to count_remaining() at loop.py:319, mirroring loop.py:213. Verify both the during-iteration and between-iteration JSON snapshots agree.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 _update_after_iteration in ralph/loop.py calls tasks.count_remaining(whitelist=...) with the same whitelist passed to start-of-iteration write
- [x] #2 Test: synthetic whitelist run with 3 whitelisted tasks (2 still To Do after iteration 1) — JSON snapshot between iteration 1 and iteration 2 has tasks_remaining=2, NOT the whole To Do count
- [x] #3 Test: synthetic non-whitelist run — tasks_remaining behavior unchanged from current (reflects whole queue, no regression)
- [x] #4 Run summary's 'Remaining: N tasks' value matches the JSON tasks_remaining field after iteration completes
- [x] #5 uv run pyright skills/ralph-run/scripts passes
- [x] #6 uv run ruff check skills/ralph-run/scripts passes
- [x] #7 uv run pytest skills/ralph-run/tests/ passes
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Add whitelist param to _update_after_iteration in loop.py and pass it through to count_remaining(); 2) Update all 3 callsites (timeout error, iteration failure, success) to pass whitelist; 3) Write test in test_loop_whitelist_tasks_remaining.py: synthetic 3-task whitelist where after iter 1 → 2 still To Do; assert JSON tasks_remaining=2 between iterations; 4) Add non-whitelist regression test; 5) Run pyright + ruff + pytest.
<!-- SECTION:NOTES:END -->
