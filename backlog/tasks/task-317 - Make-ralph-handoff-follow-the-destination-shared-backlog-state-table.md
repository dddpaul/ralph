---
id: TASK-317
title: Make ralph-handoff follow the destination shared-backlog state table
status: To Do
assignee: []
created_date: '2026-11-04T14:54:00Z'
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
- [ ] #1 With destination marker sharedBacklog true and clone switch on, the skill creates through the plugin create and reports the ID as final only after create returns 0
- [ ] #2 With destination marker true and clone switch off or unset, the skill refuses and names the enable step
- [ ] #3 With destination marker absent or false and clone switch on, the skill creates through the protocol
- [ ] #4 With destination marker absent or false and clone switch off or unset, the skill keeps the uncommitted file with a provisional ID
- [ ] #5 Tests cover the four states and destinations that are behind origin, ahead of it, dirty and on a task branch
- [ ] #6 ruff, pytest and bats pass
<!-- AC:END -->
