---
id: TASK-328
title: >-
  Move this repo's pre-push behind the plugin pre-push shim after the plugin
  update
status: To Do
assignee: []
created_date: '2026-11-06T17:47:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-311
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-311 shipped plugins/ralph/git-hooks/pre-push and showed, in a scratch repo (tests/shell/shared-backlog-prepush-test.sh), that the version-bump guard keeps running as pre-push.local behind the plugin shim. The live move in this clone waits until the installed ralph plugin carries git-hooks/pre-push. Until then, this clone has ralph.pluginHooks true, so the shim cannot resolve a pre-push body and fails closed. Every push would be blocked, and --no-verify would also skip version-bump-guard. Run this on the macOS host, never in the devcontainer, because the container shares the host's .git.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The installed ralph plugin (installed_plugins.json, the ralph@dddpaul-ralph entry) has git-hooks/pre-push before anything is moved
- [ ] #2 .git/hooks/pre-push (the version-bump wrapper) is moved to .git/hooks/pre-push.local and the plugin shim templates/shims/git-hook is installed as .git/hooks/pre-push (cmp shows they are equal)
- [ ] #3 A real push of master carrying a bumped commit runs the version-bump guard (a push with an unbumped shipped change is still refused) and lands on origin
- [ ] #4 README.md and .claude/hooks/version-bump-guard.sh describe the guard as wired through pre-push.local
<!-- AC:END -->
