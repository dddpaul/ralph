---
id: TASK-312
title: Publish each completed Ralph iteration through integrate in enforcing clones
status: To Do
assignee: []
created_date: '2026-11-04T14:54:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-309
  - TASK-311
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In enforcing clones, publish through integrate after each completed iteration.

When a publish fails:
- the run stops before the next claim, even with on-error=continue;
- no final retry follows.

--no-push in an enforcing clone is allowed only with tasks=N for a single task. The claim is still pushed, but the work is not. This is an owner decision.

Clones that don't enforce keep the single end-of-run push, and their reports now classify the failure.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-018.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 In a clone with ralph.sharedBacklog true, the orchestrator runs shared-backlog.sh integrate --task N after each completed iteration that advanced master and at the end of the run unless an earlier publish failed
- [ ] #2 A failed publish stops the run before the next claim even with on-error=continue, and no automatic final retry follows
- [ ] #3 In an enforcing clone --no-push is allowed only with tasks=N naming one task: the claim is still pushed and the work is not published
- [ ] #4 Any other --no-push run in an enforcing clone is refused at preflight
- [ ] #5 Clones that do not enforce keep the single end-of-run push and the report names the failure class: non-fast-forward, auth, hook or unreachable
- [ ] #6 The shared-mode lifecycle is reachable only in a clone with ralph.sharedBacklog true, which enable cannot set while the release gate is closed; tests open the gate explicitly
- [ ] #7 ruff, pytest and bats pass
<!-- AC:END -->
