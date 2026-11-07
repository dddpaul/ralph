---
id: TASK-337
title: Publish failed iterations that moved master in shared-backlog clones
status: To Do
assignee: []
created_date: '2026-11-07T21:35:00Z'
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
- [ ] #1 A timed-out iteration that advanced master is published before the next claim (pytest with a fake tool)
- [ ] #2 A failed iteration under on-error=continue that advanced master is published before the next claim (pytest)
- [ ] #3 An iteration that did not move master publishes nothing (pytest)
- [ ] #4 A failed publish after such an iteration still ends the run, with no end-of-run retry (pytest)
- [ ] #5 A run refused at startup in an enforcing clone writes a status file with state failed and the refusal message (pytest)
- [ ] #6 ruff and pytest pass
<!-- AC:END -->
