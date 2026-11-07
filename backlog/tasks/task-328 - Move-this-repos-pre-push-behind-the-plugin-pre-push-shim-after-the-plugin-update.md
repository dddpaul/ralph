---
id: TASK-328
title: >-
  Move this repo's pre-push behind the plugin pre-push shim after the plugin
  update
status: In Progress
assignee: []
created_date: '2026-11-06T17:47:00Z'
updated_date: '2026-11-07T14:20:00Z'
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
- [x] #1 The installed ralph plugin (installed_plugins.json, the ralph@dddpaul-ralph entry) has git-hooks/pre-push before anything is moved
- [x] #2 .git/hooks/pre-push (the version-bump wrapper) is moved to .git/hooks/pre-push.local and the plugin shim templates/shims/git-hook is installed as .git/hooks/pre-push (cmp shows they are equal)
- [ ] #3 A real push of master carrying a bumped commit runs the version-bump guard (a push with an unbumped shipped change is still refused) and lands on origin
- [x] #4 README.md and .claude/hooks/version-bump-guard.sh describe the guard as wired through pre-push.local
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Autonomous run 2026-11-07 stopped before any change: the loop ran in the devcontainer (/.dockerenv present), and this task must run on the macOS host only because the container shares the host's .git. Read-only precheck for AC #1: installed_plugins.json ralph@dddpaul-ralph points to cache/dddpaul-ralph/ralph/0.22.2 (gitCommitSha 5dc8d66), and git-hooks/pre-push is present there. So the AC #1 precondition now holds, but it is left unchecked for the host run to confirm. .git/hooks/pre-push is still the 362-byte version-bump wrapper, with no pre-push.local. Nothing was moved or pushed.

Plan (interactive, macOS host, 2026-11-07): Ralph declined in the devcontainer, as the task requires. AC#1: read installed_plugins.json for the ralph@dddpaul-ralph installPath and check git-hooks/pre-push there. AC#2: mv .git/hooks/pre-push to pre-push.local, install templates/shims/git-hook as .git/hooks/pre-push, cmp. AC#3: real pushes from this clone through the new chain to a scratch bare remote: an unbumped shipped change is refused by the version-bump guard, a bumped one lands; the live push of a bumped commit to origin follows with the next shipped push from this host (TASK-320), because the box lands first. AC#4: README (version-bump guard paragraphs, this-repo migration sentence) and the version-bump-guard.sh header describe pre-push.local behind the plugin shim. Branch starts at origin/master 5dc8d66 so it can land on top of the box's push.

AC#1: installed_plugins.json ralph@dddpaul-ralph installPath is .../ralph/0.22.2, and its git-hooks/pre-push exists (2162 bytes).
AC#2 (macOS host, 2026-11-07): .git/hooks/pre-push (the TASK-214 version-bump wrapper) moved to .git/hooks/pre-push.local; plugins/ralph/skills/ralph-init/templates/shims/git-hook copied to .git/hooks/pre-push, mode 755; cmp shows them equal. Needed the sandbox bypass: the sandbox denies writes to .git/hooks.
AC#3 (scratch part): from a temporary worktree of this clone (same .git/hooks), pushes to a scratch bare remote seeded at 5dc8d66: an unbumped shipped change (a comment in plugins/ralph/skills/ralph-run/SKILL.md) was refused by the version-bump guard ('BLOCKED: shipped plugin files changed but the plugin version was not bumped', rc=1, remote unchanged); a commit bumping both manifests to 0.22.3 then landed (5dc8d66..b1608a1, rc=0). Worktree, branch and remote removed. The live part (a bumped push of master landing on origin) is still open: the box lands TASK-312/313/315 first, and the next shipped push from this host is TASK-320.
AC#4: README (version-bump guard paragraph and this repo's migration sentence) and the version-bump-guard.sh header now describe the wrapper as pre-push.local behind the plugin shim, with the unmoved-clone case. Both shipped-set lists there were stale since TASK-322 and now name git-hooks/** and scripts/** too.
Checks: ruff clean; /bin/bash -n on the guard; bats 224/224; pytest outside the sandbox 1436 passed, 5 skipped, 1 failed: test_shared_backlog_retry, the known macOS BSD wc bug that TASK-320 AC#6 fixes.

Commit: `59ad0b7` - task-328: describe the version-bump wrapper as pre-push.local behind the plugin pre-push shim
<!-- SECTION:NOTES:END -->
