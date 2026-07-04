---
id: TASK-199
title: 'Fix orphaned RALPH_SCRIPT: 71 bash tests source an untracked ralph.sh'
status: To Do
assignee: []
created_date: '2026-07-04 08:00'
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
- [ ] #1 Root cause chosen and documented: RALPH_SCRIPT either points at a tracked, sourceable ralph.sh, or the affected bash tests are ported/retired to the Python orchestrator
- [ ] #2 No .bats test fails with 'No such file or directory' sourcing RALPH_SCRIPT
- [ ] #3 Full bats suite (bats tests/unit tests/integration tests/e2e) passes: 0 failures
- [ ] #4 uv run pytest still passes (no regression to the 185 Python tests)
- [ ] #5 uv run ruff check . passes
<!-- AC:END -->
