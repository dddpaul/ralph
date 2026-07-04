---
id: TASK-200
title: Audit Python orchestrator behavior deltas surfaced by TASK-199 bats retirement
status: To Do
assignee: []
created_date: '2026-07-04 09:40'
updated_date: '2026-07-04 09:48'
labels:
  - tech-debt
  - python-orchestrator
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-199 retired bats tests that pinned bash-orchestrator behaviors the Python port does NOT replicate. Each is either an intentional simplification or a real gap — a human should triage. Deltas found: (1) --on-error retry / --retry-count: args.py accepts them (choices include 'retry') but loop.py treats 'retry' identically to 'continue' — a failed iteration is never re-run. (2) --log-file: parsed into args.log_file but never consumed anywhere in the loop/tools (grep: only args.py references it) — the flag is a silent no-op. (3) Task-summary block-count warning: signals.py computes task_summary_count and test_signals.py covers it, but loop.py never emits the bash 'WARNING: Iteration N produced X ## Task Summary blocks (expected 1)' message. (4) current_task null-clearing: bash re-derived current_task from the In Progress list on each status write (nulling it once the task moved to Done); Python sets current_task to the last-picked task and leaves it sticky. Reference: previously covered by tests/integration/{run-summary-integration,status-file-integration,one-task-enforcement}.bats before TASK-199.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each of the 4 deltas is classified as intentional-simplification (documented) or real-gap (fixed or has its own task)
- [ ] #2 If --on-error retry is intended to work, loop.py re-runs a failed iteration up to --retry-count times; otherwise the flag/choice is removed from args.py
- [ ] #3 If --log-file is intended to work it is consumed; otherwise it is removed from args.py and SKILL/CLAUDE docs
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From TASK-199 review (task-reviewer): also audit the stale reference tests/integration/usage-pause.bats:110 RALPH_USAGE_CHECK_SCRIPT -> plugins/ralph/skills/ralph-run/scripts/usage-check.sh (untracked; ported to Python in task-151). The survivor tests pass via ccusage mocks, but the path is dead and should be repointed or removed.
<!-- SECTION:NOTES:END -->
