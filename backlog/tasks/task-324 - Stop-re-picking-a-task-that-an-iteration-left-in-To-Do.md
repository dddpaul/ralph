---
id: TASK-324
title: Stop re-picking a task that an iteration left in To Do
status: To Do
assignee: []
created_date: '2026-11-05T05:26:00Z'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: on 2026-11-05 a Ralph run with tasks=322,302,304,305,306,307,308 spent seven of its ten iterations on TASK-302.
- Each of those iterations correctly found the task blocked, finished in about 20 seconds, left it in To Do, and changed nothing (only the first wrote a note).
- The loop in `plugins/ralph/skills/ralph-run/scripts/ralph/loop.py` calls tasks.pick_next_task again after every iteration.
- In tasks= mode, the first whitelisted task still in To Do wins, and dependencies are deliberately not applied. So the same task came back every time, and TASK-304 to TASK-308 never ran.
- Default mode has the same exposure: an unchanged lowest eligible task is picked again.

Fix: within one run, a task whose status is still To Do after its iteration is excluded from further picking. The run moves on to the next eligible task and reports every excluded task at the end. This applies in both tasks= mode and default mode.

Reporting:
- the status file gains a skipped_tasks list, so ralph-status and ralph-status-watch can show it;
- the run log and the final summary name each skipped task, with the iteration that left it in To Do.

When no eligible task remains, the run ends as it does today.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After an iteration, a task whose status is still To Do is not picked again in the same run, in both tasks= mode and default mode
- [ ] #2 The run continues with the next eligible task instead of re-picking the excluded one
- [ ] #3 backlog/.ralph-status.json gains a skipped_tasks list naming each excluded task, and the run log and final summary name each with the iteration that left it in To Do
- [ ] #4 ralph-status and ralph-status-watch show skipped_tasks when it is non-empty
- [ ] #5 Tests with a stub tool cover a whitelist whose first task stays To Do (the second task runs next), a run where every task stays To Do (each is attempted once, then the run ends), and default mode
- [ ] #6 ruff, pytest and bats pass
<!-- AC:END -->
