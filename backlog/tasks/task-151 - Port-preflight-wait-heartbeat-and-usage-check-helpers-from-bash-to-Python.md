---
id: TASK-151
title: 'Port preflight, wait-heartbeat, and usage-check helpers from bash to Python'
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
US-002 from design/ralph-python-refactor-prd.md.

Port the three bash helpers to Python while preserving the exit-code and output contracts byte-for-byte. The bash helpers remain in place until US-007 (cutover); the Python versions are unused by the orchestrator until US-006 (strangler integration).

Spec sources:
- `skills/ralph-run/scripts/preflight.sh` (full file)
- `skills/ralph-run/scripts/wait-heartbeat.sh` (full file)
- `skills/ralph-run/scripts/usage-check.sh` (full file)

Parallelizable with TASK-152 (US-003 core internals) — both depend only on TASK-150 scaffold.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `ralph/preflight.py` ports `preflight.sh`: 5 ordered fail-fast checks, single-line stdout (`OK RALPH_PATH=<path>` or `ERROR: <reason>`)
- [ ] #2 `ralph/preflight.py` runs against invoker's PWD (never `cd`); uses `os.environ['TMPDIR']` not `/tmp`; anchors backlog error parsing on the canonical error line
- [ ] #3 `ralph/wait_heartbeat.py` ports `wait-heartbeat.sh`: 10×1s poll loop, 15-second freshness criterion
- [ ] #4 `ralph/usage_check.py` ports `usage-check.sh`: exit codes 0/1/2 preserved; on exit 1, stdout includes `block_end_in_<rem>min_below_<buffer>min_buffer`; on exit 2, writes sentinel flag file `backlog/.ralph-usage-check-disabled`
- [ ] #5 Parity test per helper: feed identical inputs to bash helper and Python helper, assert identical stdout AND exit code for ≥5 scenarios per helper
- [ ] #6 Unit tests for each helper covering success path, failure path, and one edge case
- [ ] #7 `uv run pyright --strict skills/ralph-run/scripts` passes
- [ ] #8 `uv run ruff check skills/ralph-run/scripts` passes
- [ ] #9 `uv run pytest skills/ralph-run/tests/` passes
<!-- AC:END -->
