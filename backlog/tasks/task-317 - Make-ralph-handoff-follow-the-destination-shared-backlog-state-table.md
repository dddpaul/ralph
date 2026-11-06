---
id: TASK-317
title: Make ralph-handoff follow the destination shared-backlog state table
status: In Progress
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-06T18:22:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-308
  - TASK-310
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make /ralph-handoff follow the state table built from the destination's marker sharedBacklog and its clone switch ralph.sharedBacklog:
- both on: create through the protocol, and report the ID only after it is pushed;
- the marker on but the switch off: refuse, and name the enable step;
- the switch on but the marker off: create through the protocol (the switch is trusted);
- both off: today's behaviour, an uncommitted file with a provisional ID.

Owner decision: the protocol is used only when the destination opted in.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-023.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 With destination marker sharedBacklog true and clone switch on, the skill creates through the plugin create and reports the ID as final only after create returns 0
- [x] #2 With destination marker true and clone switch off or unset, the skill refuses and names the enable step
- [x] #3 With destination marker absent or false and clone switch on, the skill creates through the protocol
- [x] #4 With destination marker absent or false and clone switch off or unset, the skill keeps the uncommitted file with a provisional ID
- [x] #5 Tests cover the four states and destinations that are behind origin, ahead of it, dirty and on a task branch
- [x] #6 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add plugins/ralph/skills/ralph-handoff/scripts/handoff-create.sh with 'mode DEST' (prints protocol/refuse/local from the destination's marker .claude/ralph.json sharedBacklog and git config ralph.sharedBacklog) and 'create DEST ARGS...' (protocol: runs the plugin's scripts/shared-backlog.sh create in DEST and reports the ID as final only after it returns 0; refuse: exits 1 naming scripts/shared-backlog.sh enable; local: backlog task create, provisional ID). Wire SKILL.md Steps 1/5/6 to it. Tests in tests/python/test_handoff_create.py cover the four states and behind/ahead/dirty/task-branch destinations.
<!-- SECTION:NOTES:END -->
