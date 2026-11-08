---
id: TASK-337
title: Publish failed iterations that moved master in shared-backlog clones
status: Done
assignee: []
created_date: '2026-11-07T21:35:00Z'
updated_date: '2026-11-08T08:56:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: in a clone that enforces the shared-backlog protocol, loop.py publishes an iteration through _publish_iteration only after an exit-0 iteration. An iteration that timed out, or failed under on-error=continue, takes the continue paths in plugins/ralph/skills/ralph-run/scripts/ralph/loop.py (around lines 383-426) and is not published even when it merged to master. The next claim then fails in require_level ('local master is ahead'), the run stops, and only the end-of-run integrate publishes. So on-error=continue behaves like stop (TASK-312 and TASK-315 follow-ups).

Fix: after any non-stopping iteration that advanced master, publish it the same way as a successful one, before the next claim. A failed publish still ends the run with no final retry, as TASK-312 AC #2 requires.

Also from TASK-315: a run refused at startup in an enforcing clone writes no status file, so /ralph-status and the watch see nothing or an older run. Write a failed status with the refusal message.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A timed-out iteration that advanced master is published before the next claim (pytest with a fake tool)
- [x] #2 A failed iteration under on-error=continue that advanced master is published before the next claim (pytest)
- [x] #3 An iteration that did not move master publishes nothing (pytest)
- [x] #4 A failed publish after such an iteration still ends the run, with no end-of-run retry (pytest)
- [x] #5 A run refused at startup in an enforcing clone writes a status file with state failed and the refusal message (pytest)
- [x] #6 ruff and pytest pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: in loop._run_loop publish through _publish_iteration on the timeout and on-error=continue paths before the next claim; add write_refusal_status (loop.py) called on the prompt-file / RunSession refusals and the orchestrator no-push refusal, skipping when the status file shows a live run; tests in test_loop_shared_publish.py.

Commit: `ecfba2a` - task-337: publish timed-out and continued iterations that moved master; record startup refusals in the status file

Review: APPROVED ecfba2a0a8af7001d66c8d7a44b76d8098b81f4a

Timed-out and on-error=continue iterations that moved master now publish through _publish_iteration before the next claim; a failed publish still stops the run with no end-of-run retry. write_refusal_status records startup refusals (prompt-file, holder/run lock, no-push) as a failed status, leaving a live run's status alone. Reviewer minor (redundant except PermissionError) not taken: without it PermissionError would escape os.kill. Full pytest: 1556 passed, 4 skipped.

Commit: `3933f1b` - task-337: bump plugin version to 0.25.8 (patch)
<!-- SECTION:NOTES:END -->
