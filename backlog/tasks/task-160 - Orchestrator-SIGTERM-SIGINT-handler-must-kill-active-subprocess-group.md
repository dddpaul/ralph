---
id: TASK-160
title: Orchestrator SIGTERM/SIGINT handler must kill active subprocess group
status: To Do
assignee: []
created_date: '2026-06-21 20:26'
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
- [ ] #1 SIGTERM during tool.run() interrupts the subprocess within TERMINATE_GRACE_SEC
- [ ] #2 SIGINT during tool.run() interrupts the subprocess within TERMINATE_GRACE_SEC
- [ ] #3 exit_reason='interrupted', state='failed', exit_code=130 surfaced in status JSON
- [ ] #4 Test: spawn an orchestrator with a long-running fake tool, send SIGTERM, assert it exits in <10s with state=failed/exit_reason=interrupted
<!-- AC:END -->
