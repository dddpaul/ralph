---
id: TASK-338
title: Refuse direct handoff-create.sh create calls in opted-in autonomous runs
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
Why: plugins/ralph/hooks/autonomous-create-guard.sh refuses backlog task create, backlog draft create and promote, shared-backlog.sh create, and the ralph:ralph-handoff Skill call in an autonomous run in a clone that enforces the shared-backlog protocol. A direct Bash call of plugins/ralph/skills/ralph-handoff/scripts/handoff-create.sh create DEST ... does the skill's work without the Skill call, and the guard does not match it (TASK-317 follow-up). Add that pattern, in the same command positions the guard already handles for the other commands. handoff-create.sh mode DEST only reads state and stays allowed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 In an autonomous run in an enforcing clone, a Bash call of handoff-create.sh create is refused, with a plain, quoted and bash-prefixed path (pytest in tests/python/test_autonomous_create_guard.py)
- [ ] #2 handoff-create.sh mode is not refused (pytest)
- [ ] #3 Outside an autonomous run, or in a clone that does not enforce the protocol, handoff-create.sh create passes (pytest)
- [ ] #4 bash -n, the bash 3.2 static guard, ruff and pytest pass
<!-- AC:END -->
