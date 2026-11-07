---
id: TASK-332
title: Refuse backlog draft create and draft promote in opted-in autonomous runs
status: Done
assignee: []
created_date: '2026-11-07T17:25:00Z'
updated_date: '2026-11-07T19:03:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: plugins/ralph/hooks/autonomous-create-guard.sh (US-022, TASK-316) refuses task-ID allocation during an autonomous run in a clone with ralph.sharedBacklog true, but it matches only `backlog task(s) create` (line 51) and `shared-backlog.sh create`. That catches `backlog task create --draft` but misses two commands:

- `backlog draft promote N` turns a draft into a task and allocates the next free task ID at that moment. Verified with backlog 1.55.3 in a scratch project: DRAFT-1 was created while TASK-1 and TASK-2 existed, TASK-3 arrived, and the promote produced TASK-4. So an autonomous run can still allocate a task ID outside shared-backlog.sh create, which is what the guard exists to prevent.
- `backlog draft create` allocates a DRAFT-N ID from a per-clone counter, so two hosts can clash on draft IDs too. check-dupes refuses duplicate draft IDs at push, but only after the fact.

Scope: extend the guard's patterns to these two commands, in the same command positions it already handles for task create (line start, after a shell separator, after a cd into another repo, inside a multi-line string's first line). Leave read-only and local-only draft commands alone: list, view, edit and archive. The guard stays best effort. Do not change the shared-backlog protocol itself.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 With RALPH_AUTONOMOUS=1 in a clone whose git config ralph.sharedBacklog is true, the guard refuses backlog draft promote <N> and backlog draft create <title> with exit 2 and the record-the-follow-up-in-notes message, in the same command positions as backlog task create (pytest in tests/python/test_autonomous_create_guard.py)
- [x] #2 The same two commands pass when RALPH_AUTONOMOUS is unset or ralph.sharedBacklog is not true (pytest)
- [x] #3 backlog draft list, view, edit and archive are not refused in an enforcing autonomous run (pytest)
- [x] #4 CLAUDE.md's autonomous-mode paragraph and its ralph-init template counterpart (R11 parity) name draft create and draft promote among the forbidden commands, and the README's guard paragraph lists them
- [x] #5 bash -n and the bash 3.2 static guard pass on the hook; ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `7855f62` - task-332: refuse backlog draft create and draft promote in opted-in autonomous runs

Plan: add draft create / draft promote patterns to autonomous-create-guard.sh sharing the task-create command-position prefix; parametrized pytest over the same positions; allowed list/view/edit/archive; docs in CLAUDE.md + template, README, ralph-run SKILL.md preflight paragraph.

Commit: `55b3648` - task-332: rewrap the guard header and name draft IDs in the refusal

Review: APPROVED 55b3648d330001d9fc82280a2a90ccbff4bbb32e

Guard now refuses backlog draft create / draft promote in the same command positions as task create (shared backlog_cmd prefix); draft list/view/edit/archive pass. Refusal message says 'task or draft ID'. Docs: CLAUDE.md + template, README guard + test list, ralph-run SKILL.md preflight. ruff ok, pytest 1536 passed/4 skipped, bats 283 ok.

Commit: `e15cb10` - task-332: bump plugin version to 0.25.3 (patch)
<!-- SECTION:NOTES:END -->
