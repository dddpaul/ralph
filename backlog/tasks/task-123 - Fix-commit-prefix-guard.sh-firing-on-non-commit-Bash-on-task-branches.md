---
id: TASK-123
title: Fix commit-prefix-guard.sh firing on non-commit Bash on task-* branches
status: Done
assignee: []
created_date: '2026-05-16 18:02'
updated_date: '2026-05-17 06:44'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
See full description below — written as a heredoc edit after create.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/templates/claude/hooks/commit-prefix-guard.sh has a "case \"\$cmd\" in *\"git commit\"*) ;; *) exit 0;; esac" guard placed after cmd extraction and before the branch-name guard
- [x] #2 Manual repro: on a task-N branch, piping a non-commit Bash command (e.g. {"tool_input":{"command":"kill 1"}}) into the hook script exits 0 silently with no JSON output
- [x] #3 Manual repro: on a task-N branch, piping {"tool_input":{"command":"git commit -m \"wrong\""}} into the hook still emits the deny JSON
- [x] #4 Manual repro: on a task-N branch, piping {"tool_input":{"command":"git commit -m \"task-N: ok\""}} into the hook exits 0 silently
- [x] #5 Decision recorded in task notes: keep settings.json if: "Bash(git commit *)" directive as documentation, or remove it once internal hook guard is in place — pick one and note why
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add guard 'case "$cmd" in *"git commit"*) ;; *) exit 0;; esac' after cmd extraction, before branch-name guard, in BOTH template (skills/ralph-init/templates/claude/hooks/commit-prefix-guard.sh, canonical per AC1) and live copy (.claude/hooks/commit-prefix-guard.sh, what test suite + manual repros run against; ralph-init invariant keeps them in sync). Add bats regression test in tests/unit/pretools-hooks.bats for non-commit command on task branch. Run full bats suite. Manual repros AC2/3/4 against live hook on task-123 branch. AC5: keep settings.json 'if: Bash(git commit *)' as defense-in-depth + intent documentation.

AC5 DECISION: KEEP the settings.json 'if: "Bash(git commit *)"' directive (settings.json line 32-36). Rationale: (1) Defense-in-depth — the 'if' gate avoids invoking the script for non-commit Bash (efficiency/clarity); the new internal 'case $cmd in *git commit*' guard makes the script self-protecting when invoked via paths the glob misses (compound cmds like 'cd x && git commit', direct invocation, matcher edge cases). (2) The 'if' documents hook intent. (3) Removing it would route EVERY Bash command through the script, strictly worse. Both layers kept; internal guard is the authoritative fix.

Implemented: added 'case "$cmd" in *"git commit"*) ;; *) exit 0;; esac' guard after cmd extraction, before branch-name guard, in both skills/ralph-init/templates/claude/hooks/commit-prefix-guard.sh (canonical, AC1) and .claude/hooks/commit-prefix-guard.sh (live; ralph-init keeps these in sync). Added bats regression test 'commit-prefix-guard: ignores non-commit command on task branch (TASK-123 regression)'. pretools-hooks.bats: 25/25 pass. Pre-existing unrelated failures in tests/unit/status-file.bats (ralph.sh:376 ITERATION_STARTED_AT unbound) confirmed not caused by this task (ralph.sh untouched) — out of scope.

Commit: `c416030` - task-123: Guard commit-prefix hook to git commit invocations only

task-reviewer agent verdict: APPROVED. All 5 ACs independently verified by reviewer; full pretools-hooks.bats 25/25 pass; template/live parity confirmed (R11); status-file.bats failures confirmed pre-existing & out of scope (ralph.sh untouched).
<!-- SECTION:NOTES:END -->
