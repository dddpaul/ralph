---
id: TASK-192
title: Make wait-heartbeat read-only
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 11:58'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-188
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remove filesystem writes from wait-heartbeat.sh so it is unambiguously sandbox-covered, relocating the launch-log cleanup to the ralph-run skill step or the orchestrator. See design/ralph-marketplace-prd.md US-006.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 wait-heartbeat.sh performs no write or rm operations
- [x] #2 Launch-log cleanup happens in the ralph-run skill step or the orchestrator, and the launch log is gone after a successful launch
- [x] #3 Existing wait-heartbeat tests are updated and passing
- [x] #4 bash -n passes on the modified script
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: The wait-heartbeat subsystem's only FS write is Path('backlog/.ralph-launch.log').unlink() in ralph/wait_heartbeat.py success path (wait-heartbeat.sh is a thin shim; orchestrator loop.py never touches the launch log). (1) Remove the unlink block + update the module docstring so wait_heartbeat is read-only. (2) Relocate cleanup into ralph-run SKILL.md Step 4 by chaining '&& rm -f backlog/.ralph-launch.log' to the wait-heartbeat invocation: preserves exit codes (0 success->rm->0; 1/2 short-circuit so the log survives for the Step 5 failure tails) and stays project-dir/sandbox-covered. (3) Update test_fresh_heartbeat_deletes_launch_log -> asserts the log SURVIVES (read-only). (4) bash -n on wait-heartbeat.sh. R11 parity mirror set excludes ralph-run SKILL/py; ralph-init perm-seeding narrative (§201-220 mentioning the unlink) is TASK-193/US-007 scope, left untouched.

Commit: `a0ebf6c` - task-192: Make wait-heartbeat read-only; move launch-log cleanup to ralph-run Step 4

Implemented & task-reviewer APPROVED. wait_heartbeat.py: removed the Path('backlog/.ralph-launch.log').unlink() try/except from the success path (sole FS write; wait-heartbeat.sh is a thin exec shim, orchestrator loop.py never touched the launch log) + updated docstring — module is now read-only (remaining sys.stdout.buffer.write is stdout diagnostics, not FS). ralph-run SKILL.md Step 4: chained '&& rm -f backlog/.ralph-launch.log' onto the wait-heartbeat invocation (exit 0 -> rm runs; exit 1/2 -> && short-circuits so the log survives for the Step 5 failure tails) + updated narrative. test: renamed test_fresh_heartbeat_deletes_launch_log -> test_fresh_heartbeat_leaves_launch_log, inverted assertion to prove the log is untouched (exists + content unchanged). Gate: uv run pytest 185 passed, ruff clean, bash -n OK, shim.bats 4/4. Scope: ralph-init §201-220 perm-seeding narrative left for TASK-193/US-007 (reviewer confirmed the boundary via 193's AC#1). R11 parity mirror set excludes ralph-run SKILL/module.
<!-- SECTION:NOTES:END -->
