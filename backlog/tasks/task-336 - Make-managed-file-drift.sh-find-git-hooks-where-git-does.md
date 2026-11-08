---
id: TASK-336
title: Make managed-file-drift.sh find git hooks where git does
status: In Progress
assignee: []
created_date: '2026-11-07T21:35:00Z'
updated_date: '2026-11-08T08:33:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh compares fixed .git/hooks/<name> paths (the .git/hooks rows of its table, around lines 81-83) and skips git hooks unless <project>/.git is a directory. migrate-plugin-hooks.sh clone and preflight use git rev-parse --git-path hooks. So under core.hooksPath the drift check reads hooks clone never wrote and disagrees with preflight, and in a linked worktree (where .git is a file) it skips git hooks entirely (TASK-300, follow-up 1).

Fix: resolve the hooks directory with git -C <project> rev-parse --git-path hooks, made absolute, for the check. Keep the reported path and the accept-file key as .git/hooks/<name>, so existing managed-file-drift.accept lines keep working.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Under core.hooksPath, check compares the hooks in that directory (pytest)
- [x] #2 In a linked worktree, check compares the hooks of the git common dir instead of skipping them (pytest)
- [x] #3 Reports and the accept subcommand still use the .git/hooks/<name> key, and an existing accept line still suppresses its warning (pytest)
- [x] #4 bash -n, the bash 3.2 static guard, ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `4df7de2` - task-336: read git hooks from git's hooks directory in managed-file-drift.sh
<!-- SECTION:NOTES:END -->
