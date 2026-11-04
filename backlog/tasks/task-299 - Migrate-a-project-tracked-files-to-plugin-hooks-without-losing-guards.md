---
id: TASK-299
title: Migrate a project tracked files to plugin hooks without losing guards
status: To Do
assignee: []
created_date: '2026-11-04T14:52:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-296
  - TASK-297
  - TASK-298
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The per-project, tracked part of the one-time migration to plugin-delivered files is a deterministic script:
- it writes the marker first, so an interrupted run still enforces;
- it merges existing marker keys;
- it deletes only managed guard copies not listed in localGuards, and removes only their managed settings.json entries;
- it keeps local guards, unmanaged hooks and project-owned scripts.

It commits nothing itself. The operator commits the result once, on one host.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-005 and FR-1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh has a tracked subcommand with an optional --local-guards list
- [ ] #2 tracked writes .claude/ralph.json first, merging existing keys and setting pluginHooks true, so an interrupted run leaves plugin guards enforcing
- [ ] #3 tracked deletes only managed guard copies not in localGuards and removes only their managed settings.json entries
- [ ] #4 tracked keeps local guard files and their registrations, unmanaged hook entries, project-owned scripts and a non-empty settings.json
- [ ] #5 tracked adds the !.claude/ralph.json exception to .gitignore
- [ ] #6 Tests show a second run changes nothing and every interruption point leaves a project whose guards still enforce
- [ ] #7 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
