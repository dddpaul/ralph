---
id: TASK-151
title: 'Port preflight, wait-heartbeat, and usage-check helpers from bash to Python'
status: In Progress
assignee:
  - Claude
created_date: '2026-06-21 13:08'
updated_date: '2026-06-21 15:20'
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
- [x] #1 `ralph/preflight.py` ports `preflight.sh`: 5 ordered fail-fast checks, single-line stdout (`OK RALPH_PATH=<path>` or `ERROR: <reason>`)
- [x] #2 `ralph/preflight.py` runs against invoker's PWD (never `cd`); uses `os.environ['TMPDIR']` not `/tmp`; anchors backlog error parsing on the canonical error line
- [x] #3 `ralph/wait_heartbeat.py` ports `wait-heartbeat.sh`: 10×1s poll loop, 15-second freshness criterion
- [x] #4 `ralph/usage_check.py` ports `usage-check.sh`: exit codes 0/1/2 preserved; on exit 1, stdout includes `block_end_in_<rem>min_below_<buffer>min_buffer`; on exit 2, writes sentinel flag file `backlog/.ralph-usage-check-disabled`
- [x] #5 Parity test per helper: feed identical inputs to bash helper and Python helper, assert identical stdout AND exit code for ≥5 scenarios per helper
- [x] #6 Unit tests for each helper covering success path, failure path, and one edge case
- [x] #7 `uv run pyright skills/ralph-run/scripts` passes
- [x] #8 `uv run ruff check skills/ralph-run/scripts` passes
- [x] #9 `uv run pytest skills/ralph-run/tests/` passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Port preflight.sh → ralph/preflight.py: CLI parser, 5 fail-fast checks, single-line stdout. Uses os.getcwd() (never chdir), os.environ['TMPDIR'] for temp.
2. Port wait-heartbeat.sh → ralph/wait_heartbeat.py: 10×1s poll loop, 15s freshness criterion.
3. Port usage-check.sh → ralph/usage_check.py: exit codes 0/1/2, ccusage+jq+date probes (use subprocess), endTime parsing via fromisoformat, sentinel file on exit 2 written by caller side (preflight already does this in bash so wrapper handles same behavior).
4. Add parity test per helper: skills/ralph-run/tests/test_preflight_parity.py, test_wait_heartbeat_parity.py, test_usage_check_parity.py — each runs bash + python with same inputs/env, asserts identical stdout + exit code.
5. Add unit tests covering success, failure, edge cases.
6. Verify pyright (strict), ruff, pytest all green.

Commit: `b794a84` - task-151: Port preflight/wait-heartbeat/usage-check to Python
<!-- SECTION:NOTES:END -->
