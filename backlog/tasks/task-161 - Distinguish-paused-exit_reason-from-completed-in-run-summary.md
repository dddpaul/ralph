---
id: TASK-161
title: Distinguish paused exit_reason from completed in run summary
status: Done
assignee:
  - Claude
created_date: '2026-06-22 05:30'
updated_date: '2026-06-22 06:38'
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
- [x] #1 Run summary prints distinct text for paused vs. completed runs (no 'Exit reason: all tasks done' line when state=paused)
- [x] #2 loop.py:_run_loop paused branch no longer overwrites exit_reason to 'all tasks done'
- [x] #3 Test: synthetic paused run asserts summary contains 'paused' and does NOT contain 'all tasks done'
- [x] #4 Test: synthetic completed run still shows 'Exit reason: all tasks done'
- [x] #5 uv run pyright skills/ralph-run/scripts passes
- [x] #6 uv run ruff check skills/ralph-run/scripts passes
- [x] #7 uv run pytest skills/ralph-run/tests/ passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: option (a). Extend EXIT_REASONS in summary.py to add 'paused'; change loop.py:195 to set state.exit_reason='paused' instead of 'all tasks done'; update test_summary.py closed-set test to expect 5 strings; add loop-level test that asserts a synthetic check_and_pause=True run yields summary text containing 'paused' and NOT 'all tasks done'; add complementary completed-run test that asserts 'all tasks done' still appears. Bash-parity rationale: ralph.sh:724 sets EXIT_REASON='paused' and ralph.sh:728 calls show_summary which echoes 'Exit reason: paused'.

Commit: `bae613b` - task-161: Distinguish 'paused' exit_reason from completed in run summary

Implemented option (a): extended EXIT_REASONS to include 'paused', dropped the rewrite at loop.py:195 (now sets state.exit_reason='paused' directly). Summary now reads 'Exit reason: paused' on block-end pause, matching ralph.sh:724/728. Added tests/test_loop_paused_summary.py covering paused (AC #3) and completed (AC #4) summary text. task-reviewer: APPROVED. uv run pytest tests/ → 191 passed; pyright clean; ruff clean.
<!-- SECTION:NOTES:END -->
