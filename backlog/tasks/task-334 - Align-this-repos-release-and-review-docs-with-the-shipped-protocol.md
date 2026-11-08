---
id: TASK-334
title: Align this repo's release and review docs with the shipped protocol
status: In Progress
assignee: []
created_date: '2026-11-07T21:35:00Z'
updated_date: '2026-11-08T08:02:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: the feature review of plugin-delivered-project-files and the task notes of TASK-302 (F3), TASK-318 and TASK-330 found docs that no longer match what shipped. The owner asked for this task on 2026-11-08; that covers the TASK-302 F3 condition that changing the rules file needs the owner's approval.

1. .claude/RELEASING.md 'Resolving a version conflict', step 2, says 'merge it in, or rebase your unpushed work onto it'. A rebase rewrites reviewed commits, so they no longer match their Review: APPROVED <sha> notes and R-INFRA-6 flags them; the shared-backlog protocol also never rebases. Make it merge only and say why.

2. .claude/task-reviewer-rules.md R11:
   - The table pairs .git/hooks/post-commit and .git/hooks/commit-msg with the plugin bodies. In this migrated clone every git hook (pre-commit, commit-msg, post-commit, pre-push) is the plugin shim, plugins/ralph/skills/ralph-init/templates/shims/git-hook, and git hooks are never tracked.
   - The guard row says seven Ralph guards; this repo keeps six since TASK-330 (see localGuards in .claude/ralph.json).
   - The closing note says .claude/settings.json is legacy guard wiring 'kept until the repo migrates to plugin hooks (TASK-302)'. TASK-302 is done; say what the file holds now (the repo-local guards listed in localGuards and the SessionStart clone-hooks check from TASK-331).
   tests/unit/template-parity.bats enforces the table; keep it passing and in step.

3. R-INFRA-6 in plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md: say that a project with no remote-tracking branch should set master_provenance_since, because the checker then walks all of master (TASK-318 follow-up).

4. README.md 'Shared backlog across hosts': checks_context.devcontainer_env refuses a project path that contains whitespace (SHARED_BACKLOG_CHECKS_EXEC is split on whitespace), so integrate cannot run checks in the devcontainer for such a clone. State that limitation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .claude/RELEASING.md step 2 says to merge origin/master and never rebase, with the R-INFRA-6 reason
- [x] #2 R11 no longer pairs .git/hooks/* with the plugin hook bodies; it says a migrated clone's git hooks are the plugin shim and are not tracked
- [x] #3 R11 counts the guards as in .claude/ralph.json localGuards and describes .claude/settings.json as it is now, with no 'until the repo migrates' wording
- [x] #4 tests/unit/template-parity.bats passes and matches the updated table
- [x] #5 R-INFRA-6 says a project without a remote-tracking branch should set master_provenance_since
- [x] #6 README.md 'Shared backlog across hosts' states that devcontainer checks need a project path without whitespace
- [x] #7 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: RELEASING.md step 2 merge-only with R-INFRA-6 reason; R11 table: one row pairing the four untracked .git/hooks/* with templates/shims/git-hook, six guards per localGuards, rewrite settings.json note; parity bats: registry rows for all four hooks against the shim, drop the legacy plugin-body/prefix path; R-INFRA-6 master_provenance_since advice; README whitespace limitation.

Commit: `8613bbd` - task-334: align release, R11 and R-INFRA-6 docs with the shipped protocol
<!-- SECTION:NOTES:END -->
