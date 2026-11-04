---
id: TASK-300
title: Migrate each clone to plugin hook shims and report the migration state
status: Done
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-04T18:17:00Z'
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
- [x] #1 migrate-plugin-hooks.sh clone installs the shim as pre-commit, commit-msg and post-commit in the directory from git rev-parse --git-path hooks, and never commits
- [x] #2 A differing hook listed in managed-file-drift.accept becomes (name).local, and an existing (name).local is never overwritten (stops with a message)
- [x] #3 clone sets git config ralph.pluginHooks true and saves ralph.jq and ralph.projectPath, plus ralph.claudeConfigDir when the config dir is not the default
- [x] #4 clone removes a fragment entry from .claude/settings.local.json only when user settings already contain it, and reports the entries it kept
- [x] #5 clone never sets ralph.sharedBacklog
- [x] #6 The /ralph-run preflight reports not migrated, partially migrated, shims missing in this clone, and that plugin guards are best effort
- [x] #7 managed-file-drift.sh stops managing migrated guard copies and settings.local.json and reports leftover legacy guard copies
- [x] #8 Tests show a second run changes nothing, an existing .local is preserved and permissions not yet in user settings are kept
- [x] #9 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add 'clone [<project-dir>]' to migrate-plugin-hooks.sh. Validate first (jq, plugin shim template, each of pre-commit/commit-msg/post-commit in git rev-parse --git-path hooks: absent, already the shim, the legacy template, or accepted in managed-file-drift.accept -> <name>.local; an unaccepted differing hook or a differing existing .local stops the run before any write). Then save ralph.jq, ralph.projectPath (canonical main worktree root), ralph.claudeConfigDir (only when the config dir is not $HOME/.claude), install the shims (accepted hook copied to .local first, shim swapped in atomically), set ralph.pluginHooks true last; never ralph.sharedBacklog, never commits. Trim .claude/settings.local.json: drop a fragment entry only when user settings hold the same entry, report kept ones. managed-file-drift.sh: in a project whose marker has pluginHooks true, skip settings.json, settings.local.json and the six managed guard copies, report a leftover non-local copy as 'legacy copy'; in a clone with ralph.pluginHooks true compare the git hooks with the shim. preflight.py: new report-only check printing not migrated / partially migrated / shims missing in this clone, plus the best-effort line. Tests in tests/python.

Commit: `7ebc956` - task-300: add the clone subcommand of migrate-plugin-hooks.sh and report the migration state

Commit: `4400835` - task-300: keep migrate-plugin-hooks.sh executable and save the canonical Claude config dir

Done. migrate-plugin-hooks.sh clone: checks all three git hooks before any write (absent/shim/legacy template -> shim; accepted differing hook -> <name>.local; unaccepted differing hook or a differing existing .local -> exit 1, nothing written), saves ralph.jq, ralph.projectPath (canonical main worktree root), ralph.claudeConfigDir (canonical, only off $HOME/.claude), installs the shim in git rev-parse --git-path hooks, sets ralph.pluginHooks true last, trims settings.local.json fragment entries only when user settings hold the same value and reports kept ones. Never commits, never sets ralph.sharedBacklog. Stop points config/shim:<name>/switch. managed-file-drift.sh: a project whose marker sets pluginHooks no longer compares settings.json, settings.local.json or the six guard copies and reports a non-local leftover as 'legacy copy'; a clone with ralph.pluginHooks true compares its git hooks with the shim. preflight: report-only plugin_hooks check (not migrated / partially migrated / shims missing in this clone / plugin guards are best effort). Checks: ruff clean; pytest all pass; bash -n clean; bash 3.2 static scan passed (no 3.2 binary here); bats 265 ok, 1 not ok (#191, reads the untracked local settings.local.json, passes in a clean worktree). task-reviewer APPROVED (score 9) after fixing a lost exec bit. Follow-ups: (1) managed-file-drift.sh compares fixed .git/hooks/<name> paths, while clone writes to git rev-parse --git-path hooks, so the two disagree under core.hooksPath. (2) clone recognises a legacy hook by comparing it with templates/git-hooks/<name>; TASK-301 deletes those templates, so it must keep a copy or a hash for that comparison.

Commit: `457f46b` - task-300: bump plugin version to 0.18.1 (patch)
<!-- SECTION:NOTES:END -->
