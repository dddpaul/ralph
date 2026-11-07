---
id: TASK-315
title: Claim and push a task before every Ralph iteration in enforcing clones
status: Done
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-07T16:08:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-306
  - TASK-310
  - TASK-312
  - TASK-314
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In enforcing clones, every Ralph run claims a task and pushes the claim before working on it. That covers default mode and tasks=N alike.

Run lock:
- The run takes the run lock for its whole duration.
- It passes RALPH_RUN_LOCK_TOKEN to its own protocol calls, inside the devcontainer too.

Holder:
- It is resolved once per run and passed into the container.

Claims:
- tasks=N refuses a task another holder holds unless --force-claim is given.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-021 and FR-6, FR-7.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 In an enforcing clone the orchestrator holds the run lock for the whole run and passes RALPH_RUN_LOCK_TOKEN to its own protocol calls, including inside the devcontainer
- [x] #2 A second run, and an unrelated sync or claim in the same clone, refuse while the run lock is held (tested)
- [x] #3 The holder is resolved once per run and passed into the devcontainer as SHARED_BACKLOG_HOLDER, and a missing holder refuses the run in an enforcing clone
- [x] #4 Default mode syncs, picks the lowest eligible task, claims it, pushes the claim and re-checks it before the iteration starts, trying the next candidate when the claim loses
- [x] #5 tasks=N claims, pushes and re-checks the same way, and refuses a task held by another holder unless --force-claim is given
- [x] #6 A claim already held by this holder is accepted after the status and dependency checks
- [x] #7 Tests cover two pickers in two clones racing for one task with exactly one claim landing, a missing holder, several assignees, an already-held claim and the delegated holder inside the container
- [x] #8 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: new ralph/claims.py — RunSession (holder check, run-lock --pid, exports SHARED_BACKLOG_HOLDER + RALPH_RUN_LOCK_TOKEN for the run, run-unlock on close) and claim_next (sync, pick, claim --as, sync again and re-check; a lost claim tries the next candidate; tasks=N refuses another holder's task unless --force-claim). loop.run opens the session in enforcing clones and passes the claimed task to the prompt; devcontainer_prefix forwards both vars via --remote-env; args gain --force-claim (needs --tasks); shared-backlog claim --force also takes over another holder's task. Tests: real two-clone race, missing holder, several assignees, already held, delegated holder via a fake devcontainer, run-lock refusals.

Commit: `bdbf1b2` - task-315: claim and push a task before every Ralph iteration in enforcing clones

Commit: `baa1db5` - task-315: refuse --prompt-file in enforcing clones and clear the ruff findings

Review 1 (CHANGES REQUESTED) addressed: ACs checked off; loop.py RUF100 fixed and the repo-wide ruff findings (50 on master under the locked ruff 0.17.3) cleared mechanically so uv run ruff check . passes; --prompt-file refused in enforcing clones (test added); docs say --force-claim also skips the dependency check; the new claim refusal no longer names a person. Not changed: a run refused at RunSession.open (no holder, lock held) writes no status file — the refusal is on stderr / the launch log, like the other startup refusals (--no-push, arg validation).

Review: APPROVED baa1db583f6014c9f862742aacb906213343554f

Done: ruff check . passes; pytest 1489 passed, 4 skipped; bats 0 failures; shared-backlog-claim-test 55/0. Follow-up: two older shared-backlog.sh refusal messages (release, deps) still say "on Paul's say-so" — reword them without a personal name. Follow-up: a run refused at startup in an enforcing clone writes no status file.

Commit: `c4dce43` - task-315: bump plugin version to 0.25.0 (minor)
<!-- SECTION:NOTES:END -->
