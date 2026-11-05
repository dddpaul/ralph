---
id: TASK-322
title: Count the git-hooks and scripts plugin folders as shipped files
status: To Do
assignee: []
created_date: '2026-11-05T04:54:00Z'
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
- [ ] #1 `.claude/hooks/lib/shipped-set.sh` is_shipped returns 0 for paths under plugins/ralph/git-hooks/ and plugins/ralph/scripts/, and its header comment lists both folders
- [ ] #2 bats tests show a change confined to plugins/ralph/git-hooks/ makes bump-version.sh --auto bump the patch version
- [ ] #3 bats tests show a change confined to plugins/ralph/scripts/ makes bump-version.sh --auto bump the patch version
- [ ] #4 bats tests show version-bump-guard.sh refuses a master push that changes either folder without a version bump
- [ ] #5 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
