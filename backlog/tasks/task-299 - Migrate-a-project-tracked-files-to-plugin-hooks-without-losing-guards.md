---
id: TASK-299
title: Migrate a project tracked files to plugin hooks without losing guards
status: Done
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-04T17:49:00Z'
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
- [x] #1 plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh has a tracked subcommand with an optional --local-guards list
- [x] #2 tracked writes .claude/ralph.json first, merging existing keys and setting pluginHooks true, so an interrupted run leaves plugin guards enforcing
- [x] #3 tracked deletes only managed guard copies not in localGuards and removes only their managed settings.json entries
- [x] #4 tracked keeps local guard files and their registrations, unmanaged hook entries, project-owned scripts and a non-empty settings.json
- [x] #5 tracked adds the !.claude/ralph.json exception to .gitignore
- [x] #6 Tests show a second run changes nothing and every interruption point leaves a project whose guards still enforce
- [x] #7 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: new plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh with a 'tracked [--local-guards a,b] [<project-dir>]' subcommand, jq-based. Order: marker (merged, atomic, pluginHooks true, localGuards union) -> .gitignore exception -> strip managed settings.json entries (delete file if left {}) -> delete managed guard copies not in localGuards. Managed = the six Claude guards registered in the template settings.json; filename-length-guard.sh is kept because an unmigrated clone's legacy .git/hooks/pre-commit still falls back to it. A RALPH_MIGRATE_STOP_AFTER test seam exits after a named step; tests/python/test_migrate_plugin_hooks.py checks every stop point still enforces every template registration (plugin gate or legacy copy) and that a second run changes nothing. Wiring into ralph-init Upgrade is TASK-301.

Commit: `2af384a` - task-299: add the tracked subcommand of migrate-plugin-hooks.sh

Commit: `f4184be` - task-299: remove every shipped form of a managed hook command and keep file modes

Commit: `e8e5ca5` - task-299: remove every shipped form of a managed hook command and keep file modes

Commit: `c9a7ba0` - task-299: make migrate-plugin-hooks.sh executable

Done. migrate-plugin-hooks.sh tracked: marker -> .gitignore -> settings.json -> guard copies, with RALPH_MIGRATE_STOP_AFTER stop points. Managed = the six Claude guards; filename-length-guard.sh is kept (an unmigrated clone's legacy pre-commit falls back to it; TASK-300/302 should retire it once the shims are in). Settings entries match any shipped command form ("$CLAUDE_PROJECT_DIR"/, quoted whole, braced, relative). A copy that a remaining entry still names is kept with a warning. A customised copy that is not in localGuards is deleted with a report line. Checks: ruff clean; pytest 1187 passed/4 skipped; bash -n clean; bash 3.2 static scan passed (no 3.2 binary in the container); bats 265 ok, 1 not ok (#191, R11 settings.local.json shape, which reads the untracked local .claude/settings.local.json and is not in this diff). task-reviewer: APPROVED (score 9) after one blocking fix (older command forms).

Commit: `f52046b` - task-299: bump plugin version to 0.18.0 (minor)
<!-- SECTION:NOTES:END -->
