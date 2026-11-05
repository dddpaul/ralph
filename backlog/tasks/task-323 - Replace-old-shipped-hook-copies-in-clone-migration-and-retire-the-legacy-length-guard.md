---
id: TASK-323
title: >-
  Replace old shipped hook copies in clone migration and retire the legacy
  length guard
status: In Progress
assignee: []
created_date: '2026-11-05T05:25:00Z'
updated_date: '2026-11-05T06:50:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-300
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: migrating a real project (a sibling Ralph project, dry run on 2026-11-05) showed three gaps in `plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh`.

(a) clone refuses old, unedited copies of the plugin's own git hooks.
- plan_hooks replaces a hook only when it is byte-identical to the current plugin body (`plugins/ralph/git-hooks/<name>`). Every other hook not listed in .claude/managed-file-drift.accept is refused.
- Every Ralph project created before the move carries an older shipped copy. In the dry run, its pre-commit equals the v0.14.14 template (also v0.14.7) and its commit-msg equals the v0.16.0 template, so clone exits 1 on both.
- Accepting them would keep an outdated hook running first as <name>.local, which is wrong for an unedited copy.
- Fix: ship the sha256 of every git hook body that ralph-init has ever shipped (pre-commit, commit-msg, post-commit), taken from this repo's history of the templates/git-hooks/ and plugins/ralph/git-hooks/ copies. clone replaces any hook that matches one, and still refuses unknown content.

(b) Nothing ever retires `.claude/hooks/filename-length-guard.sh`.
- tracked keeps it on purpose and prints nothing about it. It is the fallback the legacy pre-commit calls in a clone that has not run clone yet.
- Once every clone has migrated, it remains as a dead tracked copy.
- Fix: an explicit retire step deletes it. The preflight names the leftover copy as removable once this clone's pre-commit is the shim.

(c) clone must not run inside the devcontainer.
- The container shares the host's .git/config, so clone run there records container values as this clone's settings: ralph.projectPath=/workspace and the container's jq path.
- An autonomous run on 2026-11-05 avoided this only by its own judgment.
- Fix: clone refuses when DEVCONTAINER=true, with a message saying to run it on the host.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The plugin ships the sha256 of every pre-commit, commit-msg and post-commit body ralph-init has ever shipped, and a test regenerates the list from git history and fails on drift
- [x] #2 migrate-plugin-hooks.sh clone replaces a hook whose sha256 is in that list and still refuses a hook with unknown content
- [x] #3 A fixture with a pre-commit equal to the v0.14.14 template and a commit-msg equal to the v0.16.0 template migrates with clone exit 0 and both replaced by the shim
- [x] #4 An explicit retire step (for example tracked --retire-legacy) deletes .claude/hooks/filename-length-guard.sh, and the preflight names the leftover copy as removable when this clone pre-commit is the shim
- [x] #5 clone exits non-zero with a run-it-on-the-host message when DEVCONTAINER=true and writes nothing
- [x] #6 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: ship shipped-git-hooks.sha256 (name sha256 per line) beside migrate-plugin-hooks.sh, regenerated from git history in tests/python/test_shipped_git_hooks.py; clone replaces listed hooks, refuses DEVCONTAINER=true; tracked --retire-legacy deletes .claude/hooks/filename-length-guard.sh (refuses unless this clone's pre-commit is the shim); preflight names the leftover copy; managed-file-drift skips the missing copy in a shimmed migrated clone.
<!-- SECTION:NOTES:END -->
