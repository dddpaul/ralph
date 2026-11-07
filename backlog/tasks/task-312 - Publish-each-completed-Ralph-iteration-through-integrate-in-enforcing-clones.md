---
id: TASK-312
title: Publish each completed Ralph iteration through integrate in enforcing clones
status: Done
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-07T14:28:00Z'
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
- [x] #1 In a clone with ralph.sharedBacklog true, the orchestrator runs shared-backlog.sh integrate --task N after each completed iteration that advanced master and at the end of the run unless an earlier publish failed
- [x] #2 A failed publish stops the run before the next claim even with on-error=continue, and no automatic final retry follows
- [x] #3 In an enforcing clone --no-push is allowed only with tasks=N naming one task: the claim is still pushed and the work is not published
- [x] #4 Any other --no-push run in an enforcing clone is refused at preflight
- [x] #5 Clones that do not enforce keep the single end-of-run push and the report names the failure class: non-fast-forward, auth, hook or unreachable
- [x] #6 The shared-mode lifecycle is reachable only in a clone with ralph.sharedBacklog true, which enable cannot set while the release gate is closed; tests open the gate explicitly
- [x] #7 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: push.py gains shared_backlog_enforced() (git config --bool ralph.sharedBacklog), publish_after_iteration() running plugin scripts/shared-backlog.sh integrate --task N, classify_push_failure() for plain git push (non-fast-forward/auth/hook/unreachable), and a no-push refusal check. loop.py: in an enforcing clone snapshot master before each iteration and integrate after each exit-0 iteration that advanced it; a failed publish ends the run (exit_reason error, even on-error=continue) and skips the end-of-run publish; else end-of-run integrate when master moved since the last publish. Non-enforcing clones keep the single end-of-run git push, now with the failure class. ralph_orchestrator.main refuses --no-push/RALPH_NO_PUSH in an enforcing clone unless --tasks names one task (preflight before the loop). Tests: unit with stubs + real shared-backlog.sh integrate against a bare origin with the release gate opened by SHARED_BACKLOG_ALLOW_UNRELEASED=1 for enable.

Commit: `20fd4f8` - task-312: publish each completed iteration through shared-backlog integrate in enforcing clones

Lint: uv.lock is gitignored, so this venv floats to ruff 0.17.3, which reports 49 findings already on master (new default rules). The pinned-floor check uv tool run ruff@0.15.0 check . passes; vs master under 0.17.3 this branch adds only one RUF100 on an E402 noqa that matches the adjacent import and that ruff 0.15 needs.
AC #3 claim: TASK-315 adds the claim push; this task keeps --no-push to publishing only, so that claim push is unaffected by it.
Follow-up: pin ruff in pyproject (or commit uv.lock) so uv run ruff check . is reproducible; under 0.17.3 master has 49 findings.

Review: APPROVED 20fd4f84abd7d816f73cf49abd44cc37a9d17719

Follow-up (TASK-315): a timed-out or failed iteration (on-error=continue) that still advanced master is published only at the end of the run; once a claim precedes each iteration, require_level will refuse that claim while local master is ahead, so the claim step must publish or stop first.

Done: enforcing clones (ralph.sharedBacklog true) publish via plugin shared-backlog.sh integrate --task N after each exit-0 iteration that moved master and at run end unless a publish failed; a failed publish ends the run (exit = integrate rc) with the local master state reported. --no-push/RALPH_NO_PUSH there needs --tasks with one task, refused by ralph-run preflight (--no-push flag) and orchestrator startup. Plain git push failures now name non-fast-forward/auth/hook/unreachable/rejected. Final: pytest 1463 passed/4 skipped, bats 0 failures, ruff@0.15.0 clean.

Commit: `83a8ebd` - task-312: bump plugin version to 0.23.0 (minor)
<!-- SECTION:NOTES:END -->
