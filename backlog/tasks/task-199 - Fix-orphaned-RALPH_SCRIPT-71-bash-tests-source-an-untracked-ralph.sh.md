---
id: TASK-199
title: 'Fix orphaned RALPH_SCRIPT: 71 bash tests source an untracked ralph.sh'
status: Done
assignee: []
created_date: '2026-07-04 08:00'
updated_date: '2026-07-04 09:48'
labels:
  - tech-debt
  - tests
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Discovered during TASK-198. tests/helpers/common.bash line 10 sets RALPH_SCRIPT="$PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts/ralph.sh", but that file is NOT tracked in git (git ls-files finds only the two thin shims: ./ralph.sh and plugins/ralph/skills/ralph-init/templates/root/ralph.sh; git log for the RALPH_SCRIPT path is empty). TASK-188 (4c89342, ralph-marketplace relocation) repointed RALPH_SCRIPT to that path while the bash arg-parsing/loop surface moved to the Python orchestrator (ralph_orchestrator.py + ralph/ package; 185 pytest tests green). The bash unit/integration .bats still do 'RALPH_SOURCE_ONLY=1 source $RALPH_SCRIPT' and fail with 'No such file or directory'. Net effect: the full bats suite is 108 ok / 71 not ok on clean master (reproduced by TASK-198 and its reviewer). shim.bats and the Python suite are unaffected. Decide the remediation direction: either (a) restore/port a sourceable canonical bash ralph.sh at the RALPH_SCRIPT path exposing the functions the tests source, or (b) repoint RALPH_SCRIPT and port/retire the affected bash tests to match the Python orchestrator. Verify baseline first: git stash any WIP, run 'bats tests/unit tests/integration tests/e2e' (or 'bats --recursive tests/'), confirm 71 failures all trace to the missing source target.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Root cause chosen and documented: RALPH_SCRIPT either points at a tracked, sourceable ralph.sh, or the affected bash tests are ported/retired to the Python orchestrator
- [x] #2 No .bats test fails with 'No such file or directory' sourcing RALPH_SCRIPT
- [x] #3 Full bats suite (bats tests/unit tests/integration tests/e2e) passes: 0 failures
- [x] #4 uv run pytest still passes (no regression to the 185 Python tests)
- [x] #5 uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan / Root cause (AC#1): The bash orchestrator was removed in task-156 (cutover to Python) and relocated in task-188; RALPH_SCRIPT="$PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts/ralph.sh" points at a path that has never existed in git. Chosen remediation = direction (b): repoint/retire the orphaned bash tests to match the Python orchestrator. Option (a) rejected — resurrecting the deleted ~800-line bash orchestrator would regress the entire Python migration. The orchestrator behavior is now owned by 185 pytest tests (test_orchestrator_args, test_summary, test_status, test_preflight, test_signals, test_usage_check, test_loop_*). Baseline: bats 108 ok / 71 not ok. Plan: (1) delete fully-obsolete bats files that source the dead ralph.sh or a deleted .sh (argument-validation, run-summary, status-file, dependency-checks, usage-check, interrupt-trap, timeout-handling, one-task-enforcement); (2) surgically drop only the failing tests in still-useful shim->Python integration files (run-summary-integration, status-file-integration, on-error-continue, usage-pause), keeping their passing smoke tests; (3) remove the orphaned RALPH_SCRIPT pointer from tests/helpers/common.bash. Follow-up task to be filed for Python behavior deltas the retired tests covered (--on-error retry, --log-file, task-summary-count warning, current_task null-clearing).

Follow-up filed: TASK-200 tracks the 4 Python orchestrator behavior deltas (--on-error retry no-op, --log-file no-op, task-summary-count warning not emitted, current_task sticky vs null-cleared) that the retired bats tests previously pinned.

Commit: `a090c1c` - task-199: Retire orphaned bash-orchestrator bats tests (dead RALPH_SCRIPT); orchestrator coverage now owned by the 185-test pytest suite

Done: task-reviewer APPROVED. bats 108/71 -> 102 ok / 0 failures; uv run pytest 185 passed; uv run ruff clean. Deleted 8 obsolete bats files, surgically trimmed 4 shim->Python integration files (kept passing smoke tests), removed orphaned RALPH_SCRIPT from tests/helpers/common.bash. No pytest coverage lost; behavior deltas tracked in TASK-200.
<!-- SECTION:NOTES:END -->
