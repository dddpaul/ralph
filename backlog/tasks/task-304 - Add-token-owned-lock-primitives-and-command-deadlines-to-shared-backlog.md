---
id: TASK-304
title: Add token-owned lock primitives and command deadlines to shared-backlog
status: In Progress
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-05T17:20:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-303
  - TASK-322
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add reusable lock primitives and command deadlines to the shared-backlog script.

Locks:
- Two lock types, protocol and run, are atomic directories under the canonical git common dir. Each owner file holds a token, the host, a container flag, the pid and the start time.
- Only the owner releases a lock.
- A stale lock is reclaimed only when its owner provably died in the same host and pid namespace.
- While a run lock is held, mutating protocol commands refuse unless they carry RALPH_RUN_LOCK_TOKEN.
- Read-only validation takes no lock.

Deadlines: every protocol subcommand gets a total deadline.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-010 and FR-7, FR-11.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A reusable primitive creates a protocol lock and a run lock atomically as directories under the canonical git common dir, with an owner file holding a random token, host, container flag, pid and start time
- [x] #2 An operation releases only a lock whose token is its own
- [x] #3 A stale lock is reclaimed only when its owner was on the same host and pid namespace and the pid is gone; otherwise it is reported and unlock --force is required
- [x] #4 Two contenders reclaiming the same stale lock do not both succeed (tested)
- [x] #5 While a run lock is held, sync, claim, release, create, integrate and renumber refuse unless RALPH_RUN_LOCK_TOKEN carries that run token
- [x] #6 check-dupes takes and checks no lock, and runs while the protocol lock is held (tested)
- [x] #7 Every protocol subcommand that touches the network or the clone runs under a total deadline (default 120 s, SHARED_BACKLOG_DEADLINE) that kills its process group, reports state and releases only its own lock
- [ ] #8 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: in plugins/ralph/scripts/shared-backlog.sh add a lock primitive (mkdir-atomic dirs shared-backlog-{protocol,run}.lock under the canonical git common dir, owner file with token/host/container/pidns/pid/started), owner-only release, stale reclaim gated on same host + pid namespace + dead pid and serialized by a per-stale-token reclaim marker, run-lock/run-unlock/unlock subcommands, a run-lock gate on sync/claim/release/create/integrate/renumber honouring RALPH_RUN_LOCK_TOKEN, and a total deadline (SHARED_BACKLOG_DEADLINE, default 120 s) that runs each protocol subcommand in its own process group and kills the group on expiry. check-dupes runs under the deadline but takes no lock. New scratch-repo suite tests/shell/shared-backlog-lock-test.sh plus a pytest runner.

Verified: bash -n clean; bash4-builtin static guard passes (plugins/ralph/skills/ralph-run/tests... no, tests/python/test_bash32_syntax.py: 14 passed, 1 skipped); tests/shell/shared-backlog-lock-test.sh: 65 passed, 0 failed under this host's bash 5.2; tests/python/test_shared_backlog_locks.py passes. AC #8's (host) clause (real /bin/bash 3.2 run) not verifiable on this Linux host -- left unchecked pending host verification, same pattern as TASK-277..280. Full repo pytest: 1288 passed/4 skipped plus 1 pre-existing unrelated failure (test_devcontainer_missing_fails in ralph-run/tests/test_preflight.py), confirmed failing on clean master too (reproduced via git stash), not caused by this change.
<!-- SECTION:NOTES:END -->
