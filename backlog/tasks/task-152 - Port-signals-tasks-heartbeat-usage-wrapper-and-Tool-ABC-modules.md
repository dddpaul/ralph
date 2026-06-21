---
id: TASK-152
title: 'Port signals, tasks, heartbeat, usage wrapper, and Tool ABC modules'
status: To Do
assignee: []
created_date: '2026-06-21 13:08'
labels:
  - 'feature:ralph-python-refactor'
dependencies:
  - TASK-150
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-003 from design/ralph-python-refactor-prd.md.

Port the orchestrator's internal building blocks: sentinel parsing, backlog CLI wrapper, heartbeat daemon thread, usage-cap wrapper that mutates StatusFile pause fields, and the abstract `Tool` protocol that both claude and opencode will implement.

Spec sources:
- `skills/ralph-run/scripts/ralph.sh` lines 475–530 (heartbeat code path)
- `skills/ralph-run/scripts/ralph.sh` lines 660–720 (task picker)
- `skills/ralph-run/scripts/ralph.sh` lines 780–850 (sentinel scanning)
- `skills/ralph-run/scripts/ralph.sh` lines 300–380 (status update functions for usage interaction)
- `skills/ralph-run/scripts/usage-check.sh` (full file — for usage.py wrapper logic)

Parallelizable with TASK-151 (US-002 helpers) — both depend only on TASK-150 scaffold.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `ralph/signals.py`: parses `<promise>COMPLETE</promise>` AND anchored `^## Task Summary$` regex; returns `IterationSignals` dataclass with `task_summary_count`, `complete`, `error_text` fields
- [ ] #2 `ralph/tasks.py`: `pick_next_task()` queries `backlog task list`, returns lowest-ID task whose dependencies are all Done; honors `--tasks` whitelist that REPLACES the lowest-ID rule
- [ ] #3 `ralph/heartbeat.py`: daemon `threading.Thread` touches `backlog/.ralph-heartbeat` every 5s; `stop()` sets a `threading.Event` and joins thread (timeout 10s); orchestrator EXIT cleans up the heartbeat file
- [ ] #4 `ralph/usage.py`: wraps `usage_check.py`; populates the 5 `paused_*` fields on StatusFile when a pause is triggered
- [ ] #5 `ralph/tools/__init__.py`: defines `Tool` ABC with `run(prompt: str, timeout_sec: int) -> ToolResult` signature; `ToolResult` includes stdout-tee path, exit code, and an `IterationSignals` instance
- [ ] #6 Unit tests for each module
- [ ] #7 Golden-file tests for signal parsing using captured sample tool-output transcripts under `tests/fixtures/`
- [ ] #8 `uv run pyright --strict skills/ralph-run/scripts` passes
- [ ] #9 `uv run ruff check skills/ralph-run/scripts` passes
- [ ] #10 `uv run pytest skills/ralph-run/tests/` passes
<!-- AC:END -->
