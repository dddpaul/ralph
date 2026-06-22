---
id: TASK-161
title: Distinguish paused exit_reason from completed in run summary
status: To Do
assignee: []
created_date: '2026-06-22 05:30'
labels:
  - 'feature:ralph-python-refactor'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When ralph pauses due to usage-cap, ralph/loop.py:193 sets state.exit_reason='all tasks done' to satisfy the closed-set assertion at loop.py:162. The run summary then prints 'Exit reason: all tasks done' even though the run paused at block-end (bash distinguishes; see ralph.sh:304-334). Strict-port deviation from bash's summary text. Close before TASK-156 cutover.

Two implementation options (pick whichever is cleaner against the existing code):
  (a) Extend EXIT_REASONS in ralph/summary.py:14 to include 'paused', drop the rewrite at loop.py:193, and add a 'paused' branch in summary.py's reason-to-text mapping.
  (b) Keep EXIT_REASONS closed; leave state='paused' as-is; emit a separate 'paused at block-end' summary line via a check on state before the exit_reason line.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Run summary prints distinct text for paused vs. completed runs (no 'Exit reason: all tasks done' line when state=paused)
- [ ] #2 loop.py:_run_loop paused branch no longer overwrites exit_reason to 'all tasks done'
- [ ] #3 Test: synthetic paused run asserts summary contains 'paused' and does NOT contain 'all tasks done'
- [ ] #4 Test: synthetic completed run still shows 'Exit reason: all tasks done'
- [ ] #5 uv run pyright skills/ralph-run/scripts passes
- [ ] #6 uv run ruff check skills/ralph-run/scripts passes
- [ ] #7 uv run pytest skills/ralph-run/tests/ passes
<!-- AC:END -->
