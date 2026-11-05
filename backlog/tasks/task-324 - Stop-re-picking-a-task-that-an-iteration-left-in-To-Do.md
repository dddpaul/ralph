---
id: TASK-324
title: Stop re-picking a task that an iteration left in To Do
status: Done
assignee: []
created_date: '2026-11-05T05:26:00Z'
updated_date: '2026-11-05T06:37:00Z'
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
- [x] #1 After an iteration, a task whose status is still To Do is not picked again in the same run, in both tasks= mode and default mode
- [x] #2 The run continues with the next eligible task instead of re-picking the excluded one
- [x] #3 backlog/.ralph-status.json gains a skipped_tasks list naming each excluded task, and the run log and final summary name each with the iteration that left it in To Do
- [x] #4 ralph-status and ralph-status-watch show skipped_tasks when it is non-empty
- [x] #5 Tests with a stub tool cover a whitelist whose first task stays To Do (the second task runs next), a run where every task stays To Do (each is attempted once, then the run ends), and default mode
- [x] #6 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: tasks.pick_next_task gains an exclude set (both modes). loop._run_loop checks the picked task's status after every non-stopping iteration; if still To Do it is recorded in _RunState.skipped (task + iteration), appended to the run log, and excluded from later picks. StatusFile gains skipped_tasks (list of {task, iteration}) at the end of the schema; golden fixtures updated. RunSummary prints a Skipped tasks section. ralph-status / ralph-status-watch SKILL.md render skipped_tasks when non-empty. New test_loop_skipped_tasks.py with a stub tool + stub backlog.

Review round 1 fix: in default and --prompt-file mode the agent picks its own task, so build_prompt now appends 'Do NOT pick these tasks ... : TASK-x, ...' once any task is skipped. This keeps the agent's pick aligned with the orchestrator's, which the To Do check relies on. The stub tool in test_loop_skipped_tasks.py chooses from the prompt the way the agent does. Evidence: pytest 1275 passed / 4 skipped; bats 282/282 ok (via npx bats); ruff 63 errors repo-wide, identical to master, none added.

Done. A task still To Do after its iteration is excluded for the rest of the run, in both modes: pick_next_task(exclude=...). Outside whitelist mode the prompt names the excluded tasks. skipped_tasks ({task, iteration}) is recorded in the status file, run log and summary, and the status skills show it. task-reviewer APPROVED (round 2). Left as follow-ups: the exit reason stays 'all specified tasks done' when every task was skipped, and the default-mode To Do check trusts the orchestrator's pick.
<!-- SECTION:NOTES:END -->
