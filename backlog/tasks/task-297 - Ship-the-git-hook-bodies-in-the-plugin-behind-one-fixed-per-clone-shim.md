---
id: TASK-297
title: Ship the git hook bodies in the plugin behind one fixed per-clone shim
status: To Do
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-04T16:56:00Z'
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
- [ ] #1 The pre-commit, commit-msg and post-commit bodies live in plugins/ralph/git-hooks/
- [ ] #2 pre-commit runs the plugin bundled filename-length-guard and falls back to the project .claude/hooks copy when run from a legacy .git/hooks install, both layouts tested
- [ ] #3 templates/shims/git-hook is one file for every hook name, embeds the TASK-295 resolver and execs the plugin body with the hook arguments
- [ ] #4 A (name).local hook in the directory from git rev-parse --git-path hooks runs first and stops the hook on failure, with arguments and pre-push stdin reaching both; a core.hooksPath clone is tested
- [ ] #5 When the plugin cannot be resolved, pre-commit and commit-msg exit 1 if ralph.pluginHooks is true, naming git commit --no-verify
- [ ] #6 When the plugin cannot be resolved, pre-push exits 1 if ralph.pluginHooks or ralph.sharedBacklog is true, naming git push --no-verify
- [ ] #7 post-commit only warns, and every hook only warns when neither switch is set
- [ ] #8 commit-msg finds the merge message via git rev-parse --git-path MERGE_MSG and a test shows it recognises a merge in progress in a linked worktree
- [ ] #9 The template git hook copies stay byte-identical to the plugin bodies, enforced by a parity test, and keep working when installed directly into .git/hooks
- [ ] #10 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
