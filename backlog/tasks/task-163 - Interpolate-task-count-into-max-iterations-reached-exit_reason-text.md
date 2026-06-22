---
id: TASK-163
title: Interpolate task count into 'max iterations reached' exit_reason text
status: Done
assignee: []
created_date: '2026-06-22 10:14'
updated_date: '2026-06-22 10:32'
labels:
  - 'feature:ralph-python-refactor'
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bash emits a templated string when the iteration loop exhausts max_iterations: 'max iterations reached (N task(s) completed)' at ralph.sh:890, with N=TASKS_COMPLETED. Python's ralph/loop.py:288-289 leaves state.exit_reason at the bare default 'max iterations reached'. Strict-port text deviation in the summary only (TASK-159 already aligned the exit code). Cosmetic but worth closing for full bash-parity logs.

Implementation choice: either (a) compute the templated string at loop.py:288-289 and assign it directly to state.exit_reason, OR (b) keep state.exit_reason='max iterations reached' as the closed-set value and inject the '(N task(s) completed)' suffix in summary.py's render path.

Option (b) is cleaner because it keeps EXIT_REASONS as a flat closed set (matches the design intent in PRD §3 US-005 AC #7) — the count is summary-presentation state, not exit-classification state. The bash idiom interpolates because bash has no separation between the two. Python should preserve the closed set and template the display.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Run summary prints 'Exit reason: max iterations reached (N task(s) completed)' with N from tasks_completed when state.exit_reason='max iterations reached'
- [x] #2 EXIT_REASONS in ralph/summary.py still contains the closed-set string 'max iterations reached' verbatim (no template inside the set)
- [x] #3 Test: synthetic max-iter run with tasks_completed=0 asserts summary contains 'max iterations reached (0 task(s) completed)'
- [x] #4 Test: synthetic max-iter run with tasks_completed=2 asserts summary contains 'max iterations reached (2 task(s) completed)'
- [x] #5 uv run pyright skills/ralph-run/scripts passes
- [x] #6 uv run ruff check skills/ralph-run/scripts passes
- [x] #7 uv run pytest skills/ralph-run/tests/ passes
- [x] #8 Summary text uses the literal 'task(s)' for any tasks_completed value (matching bash ralph.sh:890 which does not pluralize)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) summary.py — when exit_reason == 'max iterations reached', emit 'Exit reason: max iterations reached (N task(s) completed)' where N = summary.tasks_completed (literal 'task(s)', no pluralization, mirrors bash ralph.sh:890). (2) EXIT_REASONS frozenset stays unchanged. (3) Tests: new test_loop_max_iter_summary.py drives loop_module.run through tasks_completed=0 and tasks_completed=2 max-iter exits, captures stdout, asserts the templated summary line. (4) Unit-level coverage in test_summary.py: print_summary with exit_reason='max iterations reached' and tasks_completed=0 and 2.

Commit: `5f366a1` - task-163: Template task count into 'max iterations reached' summary text

Implemented Option (b): print_summary templates the '(N task(s) completed)' suffix when exit_reason='max iterations reached'; EXIT_REASONS closed set is unchanged. Six new tests (two loop-driven, four unit-level). pyright/ruff/pytest all clean (199 passed). task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
