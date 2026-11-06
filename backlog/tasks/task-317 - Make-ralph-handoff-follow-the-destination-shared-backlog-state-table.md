---
id: TASK-317
title: Make ralph-handoff follow the destination shared-backlog state table
status: Done
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-06T18:33:00Z'
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

Commit: `553dc7e` - task-317: make ralph-handoff follow the destination shared-backlog state table

Implemented plugins/ralph/skills/ralph-handoff/scripts/handoff-create.sh: 'mode DEST' prints protocol/refuse/local from the destination's .claude/ralph.json sharedBacklog (work tree root, read like enable does) and git config --bool ralph.sharedBacklog (switch checked first, so it is trusted without the marker); 'create DEST ARGS' runs the plugin's own scripts/shared-backlog.sh create (resolved relative to the helper, not the destination's shim, since a switch-on/marker-off clone may have no shim) and prints mode/id/state/path only after create returns 0, passing its exit code (2 = origin unreachable) through; refuse exits 1 naming 'cd DEST && scripts/shared-backlog.sh enable'; local runs backlog task create and reports a provisional ID. SKILL.md Step 1 reads the mode and stops on refuse; Step 5/6 use the helper and report final vs provisional; in protocol mode the AC self-check reads origin/master:<path>. Tests: tests/python/test_handoff_create.py (7 states for mode, 4 states x behind/ahead/dirty/task-branch for create, create failure reports no ID). Checks: pytest 1409 passed/4 skipped; bats 283 ok/0 not ok; ruff check . reports 49 findings identical on master (pre-existing baseline), none in changed files. Task-reviewer: APPROVED (2 minor findings fixed: checklist order, ruff baseline note). Follow-up: autonomous-create-guard.sh matches the ralph:ralph-handoff Skill call and shared-backlog.sh create, but not a direct Bash call of handoff-create.sh create; consider adding that pattern.

Commit: `57176ac` - task-317: order the handoff checklist by step; mark Done

Commit: `7d7ed55` - task-317: bump plugin version to 0.22.0 (minor)
<!-- SECTION:NOTES:END -->
