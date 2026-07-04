---
id: TASK-200
title: Audit Python orchestrator behavior deltas surfaced by TASK-199 bats retirement
status: To Do
assignee: []
created_date: '2026-07-04 09:40'
updated_date: '2026-07-04 11:53'
labels:
  - tech-debt
  - python-orchestrator
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-199 retired bats tests that pinned bash-orchestrator behaviors the Python port does NOT replicate. Each is either an intentional simplification or a real gap — a human should triage. Deltas found: (1) --on-error retry / --retry-count: args.py accepts them (choices include 'retry') but loop.py treats 'retry' identically to 'continue' — a failed iteration is never re-run. (2) --log-file: parsed into args.log_file but never consumed anywhere in the loop/tools (grep: only args.py references it) — the flag is a silent no-op. (3) Task-summary block-count warning: signals.py computes task_summary_count and test_signals.py covers it, but loop.py never emits the bash 'WARNING: Iteration N produced X ## Task Summary blocks (expected 1)' message. (4) current_task null-clearing: bash re-derived current_task from the In Progress list on each status write (nulling it once the task moved to Done); Python sets current_task to the last-picked task and leaves it sticky. Reference: previously covered by tests/integration/{run-summary-integration,status-file-integration,one-task-enforcement}.bats before TASK-199.
<!-- SECTION:DESCRIPTION:END -->


## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From TASK-199 review (task-reviewer): also audit the stale reference tests/integration/usage-pause.bats:110 RALPH_USAGE_CHECK_SCRIPT -> plugins/ralph/skills/ralph-run/scripts/usage-check.sh (untracked; ported to Python in task-151). The survivor tests pass via ccusage mocks, but the path is dead and should be repointed or removed.
<!-- SECTION:NOTES:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each of the 4 behavior deltas (--on-error retry, --log-file, task-summary-count warning, current_task null-clearing) is classified in the task notes as intentional-drop (behavior/flag removed) or real-gap (implemented in the Python orchestrator in this task)
- [ ] #2 --on-error retry: either loop.py re-runs a failed iteration up to --retry-count times AND a new pytest test asserts the retry occurs, or the retry choice/flag is removed from args.py and its SKILL/CLAUDE docs
- [ ] #3 --log-file: either the loop/tools consume it AND a new pytest test asserts log output is written to the given path, or --log-file is removed from args.py and its SKILL/CLAUDE docs
- [ ] #4 task-summary-count warning and current_task null-clearing: each is either implemented in loop.py with a passing pytest test asserting the behavior, or documented in the task notes as an intentional simplification
- [ ] #5 A coverage map in the task notes lists every behavior the TASK-199-retired bats files pinned and maps each to the owning pytest test(s); any behavior with no pytest owner is either newly covered in this task or explicitly declared intentional-drop — no entry left 'uncovered'
- [ ] #6 tests/integration/usage-pause.bats no longer references the dead RALPH_USAGE_CHECK_SCRIPT/usage-check.sh path (repointed to the Python usage check or the stale tests removed)
- [ ] #7 uv run pytest passes with test count >= 185 (reflecting any newly added tests) and uv run ruff check . passes
<!-- AC:END -->
