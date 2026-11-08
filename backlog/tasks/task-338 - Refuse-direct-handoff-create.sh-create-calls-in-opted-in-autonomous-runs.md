---
id: TASK-338
title: Refuse direct handoff-create.sh create calls in opted-in autonomous runs
status: Done
assignee: []
created_date: '2026-11-07T21:35:00Z'
updated_date: '2026-11-08T09:08:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: plugins/ralph/hooks/autonomous-create-guard.sh refuses backlog task create, backlog draft create and promote, shared-backlog.sh create, and the ralph:ralph-handoff Skill call in an autonomous run in a clone that enforces the shared-backlog protocol. A direct Bash call of plugins/ralph/skills/ralph-handoff/scripts/handoff-create.sh create DEST ... does the skill's work without the Skill call, and the guard does not match it (TASK-317 follow-up). Add that pattern, in the same command positions the guard already handles for the other commands. handoff-create.sh mode DEST only reads state and stays allowed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 In an autonomous run in an enforcing clone, a Bash call of handoff-create.sh create is refused, with a plain, quoted and bash-prefixed path (pytest in tests/python/test_autonomous_create_guard.py)
- [x] #2 handoff-create.sh mode is not refused (pytest)
- [x] #3 Outside an autonomous run, or in a clone that does not enforce the protocol, handoff-create.sh create passes (pytest)
- [x] #4 bash -n, the bash 3.2 static guard, ruff and pytest pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add a handoff-create.sh create pattern to autonomous-create-guard.sh matched anywhere (like shared-backlog.sh create, quoted or not); pytest for refused plain/quoted/bash-prefixed paths, allowed mode, and interactive/non-enforcing passes; update ralph-run SKILL.md guard list.

Commit: `6ca72c7` - task-338: refuse direct handoff-create.sh create in opted-in autonomous runs

Commit: `8bb3604` - task-338: list handoff-create.sh create among the guard's refusals in README

Review: APPROVED 8bb36045b653ac142c575ff0ef8c6e479e4dab40

Guard matches handoff-create.sh create anywhere in a Bash command (quoted or not, like shared-backlog.sh create); mode stays allowed. README and ralph-run SKILL.md list it. Full pytest 1563 passed, 4 skipped; ruff clean.

Commit: `821b373` - task-338: bump plugin version to 0.25.9 (patch)
<!-- SECTION:NOTES:END -->
