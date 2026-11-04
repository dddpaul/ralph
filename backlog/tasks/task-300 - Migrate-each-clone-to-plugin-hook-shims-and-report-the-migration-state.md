---
id: TASK-300
title: Migrate each clone to plugin hook shims and report the migration state
status: To Do
assignee: []
created_date: '2026-11-04T14:52:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-299
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The per-clone part of the one-time migration runs once on each host and never commits:
- it installs the shims;
- it keeps local hooks as (name).local;
- it sets the trusted switch ralph.pluginHooks;
- it saves ralph.jq and ralph.projectPath;
- it trims common allow rules only when user settings already hold them.

It never enables the shared-backlog protocol; that is an explicit step. The preflight reports the migration state.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-006 and FR-2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 migrate-plugin-hooks.sh clone installs the shim as pre-commit, commit-msg and post-commit in the directory from git rev-parse --git-path hooks, and never commits
- [ ] #2 A differing hook listed in managed-file-drift.accept becomes (name).local, and an existing (name).local is never overwritten (stops with a message)
- [ ] #3 clone sets git config ralph.pluginHooks true and saves ralph.jq and ralph.projectPath, plus ralph.claudeConfigDir when the config dir is not the default
- [ ] #4 clone removes a fragment entry from .claude/settings.local.json only when user settings already contain it, and reports the entries it kept
- [ ] #5 clone never sets ralph.sharedBacklog
- [ ] #6 The /ralph-run preflight reports not migrated, partially migrated, shims missing in this clone, and that plugin guards are best effort
- [ ] #7 managed-file-drift.sh stops managing migrated guard copies and settings.local.json and reports leftover legacy guard copies
- [ ] #8 Tests show a second run changes nothing, an existing .local is preserved and permissions not yet in user settings are kept
- [ ] #9 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
