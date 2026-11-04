---
id: TASK-298
title: Ship the common allow rules as a user-settings fragment in the plugin
status: To Do
assignee: []
created_date: '2026-11-04T14:52:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ship the common allow rules as one plugin fragment that lands in user settings, so that projects carry only their extras.

A plugin cannot ship allow rules itself:
- On the second host, configuration management merges the fragment.
- On the Mac, the preflight lists what is missing, and the owner adds it.

The 7 Skill(...) rules are dropped, because a test in -p mode showed skills need no allow rule. Interactive mode is still to be confirmed on the host.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-004.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 plugins/ralph/user-settings.json holds the 46 Bash rules and ScheduleWakeup from the template settings.local.json, attribution with empty commit and pr, and sandbox with enabled and autoAllowBashIfSandboxed
- [ ] #2 The fragment holds no Skill(...) rules
- [ ] #3 The /ralph-run preflight prints one warning listing exactly the fragment entries missing from the user settings and changes no file
- [ ] #4 A merge helper appends missing allow entries to a sample user settings file, keeps every unrelated key and value, and reports a differing scalar without overwriting it
- [ ] #5 (host) In an interactive session in a project without Skill(...) rules, /ralph-status runs with no permission prompt, and the result is recorded in the notes
- [ ] #6 ruff, pytest and bats pass
<!-- AC:END -->
