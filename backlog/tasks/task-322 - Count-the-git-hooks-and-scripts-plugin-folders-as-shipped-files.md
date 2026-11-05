---
id: TASK-322
title: Count the git-hooks and scripts plugin folders as shipped files
status: Done
assignee: []
created_date: '2026-11-05T04:54:00Z'
updated_date: '2026-11-05T05:04:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: `.claude/hooks/lib/shipped-set.sh` defines which plugin paths need a strictly greater plugin version. Both `.claude/hooks/bump-version.sh` (the per-task auto-bump) and `.claude/hooks/version-bump-guard.sh` (the pre-push backstop) use it.

Claude Code rebuilds its on-disk plugin cache only when the version increases. A shipped file that changes without a bump is therefore never delivered to users.

Two shipped-and-executed plugin folders are missing from the set:
- `plugins/ralph/git-hooks/`, added by TASK-297. It holds the git hook bodies that every migrated clone's shim executes.
- `plugins/ralph/scripts/`, added by TASK-303. It holds the shared-backlog script that the later protocol tasks harden and that projects will run through their shim.

The next tasks change both folders: TASK-304 to TASK-309 change scripts/shared-backlog.sh, and TASK-311 adds git-hooks/pre-push.

Fix:
- add both folders to is_shipped;
- list them in the file's header comment;
- add bats cases. A change confined to each folder must make bump-version.sh --auto bump the version, and must make version-bump-guard.sh refuse a push without a bump.

Changes under either folder count as a patch increment, as for hooks/ and user-settings.json today. Only skills/ and agents/ infer minor.

This is repo-local governance under .claude/ and is not mirrored into ralph-init templates.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `.claude/hooks/lib/shipped-set.sh` is_shipped returns 0 for paths under plugins/ralph/git-hooks/ and plugins/ralph/scripts/, and its header comment lists both folders
- [x] #2 bats tests show a change confined to plugins/ralph/git-hooks/ makes bump-version.sh --auto bump the patch version
- [x] #3 bats tests show a change confined to plugins/ralph/scripts/ makes bump-version.sh --auto bump the patch version
- [x] #4 bats tests show version-bump-guard.sh refuses a master push that changes either folder without a version bump
- [x] #5 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add plugins/ralph/git-hooks/* and plugins/ralph/scripts/* to is_shipped + header; add bats cases in bump-version.bats (newly added file per folder -> patch) and version-bump-guard.bats (blocks per folder without bump).

Commit: `f67a844` - task-322: count plugin git-hooks and scripts folders as shipped files

Added plugins/ralph/git-hooks/* and plugins/ralph/scripts/* to is_shipped and its header. New bats: bump-version --auto gives patch (0.1.0->0.1.1) for a newly added file in each folder; version-bump-guard blocks a master push changing either folder without a bump. All 4 new cases fail with the lib change reverted. Gates: ruff clean, pytest 1265 passed/4 skipped, bats 282/282, bash -n ok. task-reviewer APPROVED (score 10).
<!-- SECTION:NOTES:END -->
