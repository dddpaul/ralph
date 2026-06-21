---
id: TASK-151
title: 'Port preflight, wait-heartbeat, and usage-check helpers from bash to Python'
status: Done
assignee:
  - Claude
created_date: '2026-06-21 13:08'
updated_date: '2026-06-21 15:37'
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

Commit: `d7d9d4a` - task-151: Stabilize within-buffer parity test against subprocess jitter

Implementation complete; task-reviewer APPROVED.

**Files added:**
- skills/ralph-run/scripts/ralph/preflight.py — 5 ordered checks (6 with --block-end-buffer-min>0), single-line stdout, runs against invoker PWD, honors TMPDIR, anchored backlog 'not found' parsing.
- skills/ralph-run/scripts/ralph/wait_heartbeat.py — 10×1s polls, 15s freshness criterion, unlinks launch log on success, tails launch+run logs on failure.
- skills/ralph-run/scripts/ralph/usage_check.py — exit 0/1/2 parity with bash; CLI additionally writes sentinel flag on exit 2 (AC #4).
- skills/ralph-run/tests/conftest.py — shared PreflightFixture and bin-mock helpers.
- skills/ralph-run/tests/test_preflight.py — 18 unit tests (success/failure/edge + TMPDIR + no-chdir invariants).
- skills/ralph-run/tests/test_wait_heartbeat.py — 5 unit tests.
- skills/ralph-run/tests/test_usage_check.py — 17 unit tests covering buffer validation, PATH lookups, JSON parsing edges, sentinel CLI behavior, ISO parsing.
- skills/ralph-run/tests/test_preflight_parity.py — 9 parity scenarios (bash subprocess vs python -m ralph.preflight; identical args/env/PWD; byte-equal stdout + exit code).
- skills/ralph-run/tests/test_wait_heartbeat_parity.py — 5 parity scenarios; stale-heartbeat paths take ~10s each due to bash's real sleep.
- skills/ralph-run/tests/test_usage_check_parity.py — 10 parity scenarios; within-buffer test uses +3m30s to absorb subprocess-startup jitter.

**Verification:**
- uv run pyright skills/ralph-run/scripts → 0 errors (strict)
- uv run ruff check skills/ralph-run/ → All checks passed
- uv run pytest skills/ralph-run/tests/ → 72 passed (~48s, dominated by unavoidable bash wait-heartbeat sleeps)

**Notes for next task (TASK-152/154):**
- Python preflight's usage check honors RALPH_USAGE_CHECK_SCRIPT env override (subprocess to external script) just like bash. With env unset it calls ralph.usage_check.evaluate() in-process — faster and dependency-free.
- usage_check.evaluate(buffer_min_raw) returns (exit_code, stdout, stderr) for reuse without monkeypatching sys.stdout.
- Sentinel-on-exit-2 is written by both the usage_check CLI and preflight._check_usage; touch is idempotent, so no double-write concern.

Commit: see post-commit hook annotations.
<!-- SECTION:NOTES:END -->
