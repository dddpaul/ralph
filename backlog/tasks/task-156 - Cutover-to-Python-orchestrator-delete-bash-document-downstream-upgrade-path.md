---
id: TASK-156
title: Cutover to Python orchestrator; delete bash; document downstream upgrade path
status: To Do
assignee: []
created_date: '2026-06-21 13:09'
updated_date: '2026-06-22 05:30'
labels:
  - 'feature:ralph-python-refactor'
dependencies:
  - TASK-155
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-007 from design/ralph-python-refactor-prd.md.

The cutover task. Implement the mechanical clean-run check script, run 5 clean cycles on Python with bash still as default, flip the default to python, run 5 more clean cycles, then delete the inner bash orchestrator + helpers, simplify the outer shim back to a thin pointer at the Python orchestrator, and document the upgrade path for downstream Ralph projects.

Spec sources:
- `design/ralph-python-refactor-prd.md` §3 US-007 (full task spec)
- `design/ralph-python-refactor-prd.md` §8 success metrics (the 5-clean-runs gate)
- `design/ralph-python-refactor-prd.md` §6 final shim shape after cleanup
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `tests/scripts/check_run_clean.py --run-only` exists; codifies the 6-check gate (state=completed, exit_code=0, empty errors[], ≥1 task moved To Do→Done, heartbeat fresh throughout sampled every 5s, no leftover child processes)
- [ ] #2 `tests/scripts/check_run_clean.py --parity bash_status.json python_status.json` exists; performs schema-parity check (field set + types match)
- [ ] #3 5 consecutive `RALPH_IMPL=python` runs (with default still `bash`) each pass `--run-only`; documented in task notes with run dates and status snapshots
- [ ] #4 Default flipped to `python` in: live outer `ralph.sh`, `skills/ralph-run/SKILL.md`, `skills/ralph-init/templates/root/ralph.sh` (R11 parity preserved)
- [ ] #5 5 MORE consecutive clean runs with `python` as default (rollback still possible during this window via `RALPH_IMPL=bash`)
- [ ] #6 Delete inner bash: `skills/ralph-run/scripts/ralph.sh`, `preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`
- [ ] #7 Outer shim simplifies back to ~6 lines pointing only at the Python orchestrator (live + R11 template mirror)
- [ ] #8 `/ralph-run` skill `impl=` parameter removed (no longer needed)
- [ ] #9 `CLAUDE.md` Project-Specific Language line tightened to: "Python (orchestrator) + Bash (hooks, git hooks, sync, firewall) + Markdown (skills, agents, docs)"
- [ ] #10 Task notes include explicit downstream upgrade instructions: existing Ralph projects run `ralph-init upgrade` OR hand-patch their outer `ralph.sh` + `Dockerfile.base` from the template diffs
- [ ] #11 `uv run pyright skills/ralph-run/scripts` passes
- [ ] #12 `uv run pytest skills/ralph-run/tests/` passes
- [ ] #13 Parity test suites (test_preflight_parity.py, test_wait_heartbeat_parity.py, test_usage_check_parity.py) deleted alongside the bash helpers — they cannot pass once the bash side is gone
<!-- AC:END -->
