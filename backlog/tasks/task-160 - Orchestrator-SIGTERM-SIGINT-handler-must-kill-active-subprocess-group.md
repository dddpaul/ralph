---
id: TASK-160
title: Orchestrator SIGTERM/SIGINT handler must kill active subprocess group
status: Done
assignee:
  - Claude
created_date: '2026-06-21 20:26'
updated_date: '2026-06-22 06:30'
labels:
  - 'feature:ralph-python-refactor'
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Current Python orchestrator polls a pending-signal flag between iterations (ralph/loop.py:_SignalInstaller). If SIGTERM arrives mid-iteration the child subprocess keeps running until its own timeout. Bash trap (_kill_children at ralph.sh:582-593) walks pgrep -P $$ and SIGTERMs each direct child immediately. File as parity gap to close before US-007 cutover.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SIGTERM during tool.run() interrupts the subprocess within TERMINATE_GRACE_SEC
- [x] #2 SIGINT during tool.run() interrupts the subprocess within TERMINATE_GRACE_SEC
- [x] #3 exit_reason='interrupted', state='failed', exit_code=130 surfaced in status JSON
- [x] #4 Test: spawn an orchestrator with a long-running fake tool, send SIGTERM, assert it exits in <10s with state=failed/exit_reason=interrupted
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Modify _SignalInstaller in ralph/loop.py to track active subprocess pgid and forward SIGTERM to its process group when the handler fires (bash-parity for _kill_children at ralph.sh:582-593).
2. Extend Tool.run() ABC + ClaudeTool.run + OpencodeTool.run with an optional on_spawn callback; loop's _invoke_tool wires it to installer.set_active_subprocess.
3. Move installer.raise_if_pending() to run BEFORE the failed-iteration accounting so a signal-killed iteration surfaces as 'interrupted' rather than 'error'.
4. Add tests:
   - Unit test for handler forwarding SIGTERM to a registered subprocess (test_loop_signal_interrupt.py).
   - E2E test: spawn orchestrator with FAKE_CLAUDE_MODE=hang, send SIGTERM, assert exit in <10s with state=failed/exit_reason=interrupted in status JSON+summary stdout.

Implemented bash-parity SIGTERM/SIGINT forwarding in Python orchestrator.

Implementation:
- _SignalInstaller (loop.py) tracks the active tool subprocess via set_active_subprocess(); the handler forwards SIGTERM to its process group via os.killpg, mirroring bash _kill_children at ralph.sh:582-593.
- Tool.run() ABC + ClaudeTool + OpencodeTool gained an optional on_spawn keyword arg; loop's _invoke_tool wires it to installer.set_active_subprocess and clears on return.
- Race close: if a signal arrives between Popen and registration, set_active_subprocess re-fires the SIGTERM at register time (covered by test_set_active_subprocess_kills_when_signal_already_pending).
- Lock is threading.RLock(): signal handlers run on the main thread and can re-enter set_active_subprocess's lock — a non-reentrant Lock would deadlock (covered by test_handler_does_not_deadlock_when_lock_already_held).
- raise_if_pending() now runs BEFORE iteration-failure accounting so a signal-killed iteration surfaces as exit_reason=interrupted (in summary) rather than a generic 'error' bucket.

Tests added in tests/test_loop_signal_interrupt.py (8 cases): handler forwarding for SIGTERM/SIGINT, no-op without registration, already-exited cleanup, race-close + deadlock-guard unit tests, clear-on-None, plus an end-to-end test that spawns the orchestrator over FAKE_CLAUDE_MODE=hang, sends SIGTERM, and asserts exit in <10s with state=failed/exit_code=130/'Exit reason: interrupted' on stdout.

189/189 tests pass (3 consecutive runs). ruff clean. task-reviewer APPROVED.

Commit: `091f7e4` - task-160: Forward SIGTERM/SIGINT to active tool subprocess
<!-- SECTION:NOTES:END -->
