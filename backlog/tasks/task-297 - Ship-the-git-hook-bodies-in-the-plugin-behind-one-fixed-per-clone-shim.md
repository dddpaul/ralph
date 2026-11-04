---
id: TASK-297
title: Ship the git hook bodies in the plugin behind one fixed per-clone shim
status: Done
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-04T17:23:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-295
  - TASK-321
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make each clone's git hooks one fixed shim that runs the plugin's hook body, so that git hook changes ship with a plugin update.

The shim embeds the US-001 resolver. A local hook named (name).local runs first, from the directory git rev-parse --git-path hooks returns.

Blocking when the plugin cannot be resolved is keyed on per-clone switches, an owner decision:
- pre-commit and commit-msg block when git config ralph.pluginHooks is true;
- pre-push blocks when ralph.pluginHooks or ralph.sharedBacklog is true;
- post-commit only warns.

The bypasses are git commit --no-verify and git push --no-verify.

Two more changes:
- pre-commit uses the plugin's bundled filename-length-guard, with a fallback to the project copy for legacy installs.
- commit-msg finds the merge message through git rev-parse --git-path MERGE_MSG, which also works in linked worktrees.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-003 and FR-5.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The pre-commit, commit-msg and post-commit bodies live in plugins/ralph/git-hooks/
- [x] #2 pre-commit runs the plugin bundled filename-length-guard and falls back to the project .claude/hooks copy when run from a legacy .git/hooks install, both layouts tested
- [x] #3 templates/shims/git-hook is one file for every hook name, embeds the TASK-295 resolver and execs the plugin body with the hook arguments
- [x] #4 A (name).local hook in the directory from git rev-parse --git-path hooks runs first and stops the hook on failure, with arguments and pre-push stdin reaching both; a core.hooksPath clone is tested
- [x] #5 When the plugin cannot be resolved, pre-commit and commit-msg exit 1 if ralph.pluginHooks is true, naming git commit --no-verify
- [x] #6 When the plugin cannot be resolved, pre-push exits 1 if ralph.pluginHooks or ralph.sharedBacklog is true, naming git push --no-verify
- [x] #7 post-commit only warns, and every hook only warns when neither switch is set
- [x] #8 commit-msg finds the merge message via git rev-parse --git-path MERGE_MSG and a test shows it recognises a merge in progress in a linked worktree
- [x] #9 The template git hook copies stay byte-identical to the plugin bodies, enforced by a parity test, and keep working when installed directly into .git/hooks
- [x] #10 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: move pre-commit/commit-msg/post-commit bodies to plugins/ralph/git-hooks/ (templates stay byte-identical, live .git/hooks copies updated); pre-commit picks $(dirname $0)/../hooks/filename-length-guard.sh, else <repo>/.claude/hooks copy; commit-msg uses git rev-parse --git-path MERGE_MSG; new templates/shims/git-hook embeds the resolver, runs <name>.local from --git-path hooks first (stdin buffered for pre-push/post-rewrite/reference-transaction), execs the plugin body, and on resolve failure blocks per FR-5 switches else warns. Tests: tests/python/test_git_hook_shim.py plus bats updates for both pre-commit layouts and parity.

Commit: `777119a` - task-297: ship the git hook bodies in the plugin behind one fixed per-clone shim

Done: bodies in plugins/ralph/git-hooks/ (template copies byte-identical, parity-tested); pre-commit uses $(dirname $0)/../hooks/filename-length-guard.sh then the project .claude/hooks copy; commit-msg uses git rev-parse --git-path MERGE_MSG. templates/shims/git-hook embeds the resolver, runs <name>.local first (stdin buffered for pre-push/post-rewrite/reference-transaction via an unlinked temp file on fd 0/3), execs the body; on resolve failure it blocks per FR-5 switches, else warns. A resolved plugin lacking the body for a hook name counts as unresolved (so a pre-push shim before TASK-311 blocks when a switch is on — TASK-300 installs only pre-commit/commit-msg/post-commit). Tests: tests/python/test_git_hook_shim.py (27). Reviewer: ralph:task-reviewer APPROVED. bats 265/266: the settings.local.json R11 shape failure is pre-existing (container-masked file).

Commit: `6ad97d3` - task-297: bump plugin version to 0.17.0 (minor)
<!-- SECTION:NOTES:END -->
