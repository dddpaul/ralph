---
id: TASK-162
title: Distinguish 'all specified tasks done' from 'all tasks done' in exit_reason
status: Done
assignee: []
created_date: '2026-06-22 10:13'
updated_date: '2026-06-22 10:23'
labels:
  - 'feature:ralph-python-refactor'
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When a --tasks whitelist is in play and all whitelisted tasks complete, bash sets EXIT_REASON='all specified tasks done' (ralph.sh:743). When the general To Do queue empties, bash sets EXIT_REASON='all tasks done' (ralph.sh:751,881). Python collapses both to 'all tasks done' at ralph/loop.py:203 — strict-port text deviation in the summary. Symmetrical to the fix TASK-161 made for 'paused'.

Implementation:
1. Extend EXIT_REASONS in ralph/summary.py to include 'all specified tasks done' (set will grow to 6 strings)
2. Add a 'all specified tasks done' branch in summary.py's reason→display-text mapping
3. At ralph/loop.py:203 branch on whether the whitelist is set: if whitelist → 'all specified tasks done', else → 'all tasks done'
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 EXIT_REASONS in ralph/summary.py contains 'all specified tasks done'
- [x] #2 When --tasks whitelist is set and all whitelisted tasks complete, state.exit_reason='all specified tasks done'
- [x] #3 When no whitelist and queue empties, state.exit_reason='all tasks done' (unchanged)
- [x] #4 Run summary prints distinct text for the two cases
- [x] #5 Test: synthetic whitelist run completes all whitelisted tasks → asserts exit_reason='all specified tasks done' and summary text matches
- [x] #6 Test: synthetic non-whitelist run completes all To Do → asserts exit_reason='all tasks done' (no regression)
- [x] #7 uv run pyright skills/ralph-run/scripts passes
- [x] #8 uv run ruff check skills/ralph-run/scripts passes
- [x] #9 uv run pytest skills/ralph-run/tests/ passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: extend EXIT_REASONS in ralph/summary.py to add 'all specified tasks done' (6 strings total); update closed-set test_summary.py test to expect the 6th string; branch ralph/loop.py:203 on whitelist truthiness — whitelist set → 'all specified tasks done', else → 'all tasks done' (unchanged); add test_loop_whitelist_summary.py covering AC #5 (whitelist completes → 'all specified tasks done') and AC #6 (no-whitelist regression). Bash parity: ralph.sh:743 (whitelist exhausted) vs ralph.sh:751 (general queue empty).

Implemented: extended EXIT_REASONS to include 'all specified tasks done'; branched ralph/loop.py at pick_next_task=None on whitelist truthiness (whitelist → 'all specified tasks done', else → 'all tasks done' unchanged). Summary already prints raw exit_reason verbatim, so no separate display-mapping needed (mirrors TASK-161 shape). Added tests/test_loop_whitelist_summary.py covering AC #5 (whitelist exhausted) and AC #6 (no-whitelist regression). Updated test_summary.py closed-set test to expect 6 strings. Bash parity: ralph.sh:743 vs ralph.sh:751. uv run pytest tests/ → 193 passed; ruff clean; pyright clean. task-reviewer: APPROVED.

Commit: `f53c6ea` - task-162: Distinguish 'all specified tasks done' from 'all tasks done' in exit_reason
<!-- SECTION:NOTES:END -->
