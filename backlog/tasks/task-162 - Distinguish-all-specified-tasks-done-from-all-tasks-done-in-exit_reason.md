---
id: TASK-162
title: Distinguish 'all specified tasks done' from 'all tasks done' in exit_reason
status: To Do
assignee: []
created_date: '2026-06-22 10:13'
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
- [ ] #1 EXIT_REASONS in ralph/summary.py contains 'all specified tasks done'
- [ ] #2 When --tasks whitelist is set and all whitelisted tasks complete, state.exit_reason='all specified tasks done'
- [ ] #3 When no whitelist and queue empties, state.exit_reason='all tasks done' (unchanged)
- [ ] #4 Run summary prints distinct text for the two cases
- [ ] #5 Test: synthetic whitelist run completes all whitelisted tasks → asserts exit_reason='all specified tasks done' and summary text matches
- [ ] #6 Test: synthetic non-whitelist run completes all To Do → asserts exit_reason='all tasks done' (no regression)
- [ ] #7 uv run pyright skills/ralph-run/scripts passes
- [ ] #8 uv run ruff check skills/ralph-run/scripts passes
- [ ] #9 uv run pytest skills/ralph-run/tests/ passes
<!-- AC:END -->
