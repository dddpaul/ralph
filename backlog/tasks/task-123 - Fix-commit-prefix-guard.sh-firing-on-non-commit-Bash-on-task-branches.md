---
id: TASK-123
title: Fix commit-prefix-guard.sh firing on non-commit Bash on task-* branches
status: To Do
assignee: []
created_date: '2026-05-16 18:02'
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
- [ ] #1 skills/ralph-init/templates/claude/hooks/commit-prefix-guard.sh has a "case \"\$cmd\" in *\"git commit\"*) ;; *) exit 0;; esac" guard placed after cmd extraction and before the branch-name guard
- [ ] #2 Manual repro: on a task-N branch, piping a non-commit Bash command (e.g. {"tool_input":{"command":"kill 1"}}) into the hook script exits 0 silently with no JSON output
- [ ] #3 Manual repro: on a task-N branch, piping {"tool_input":{"command":"git commit -m \"wrong\""}} into the hook still emits the deny JSON
- [ ] #4 Manual repro: on a task-N branch, piping {"tool_input":{"command":"git commit -m \"task-N: ok\""}} into the hook exits 0 silently
- [ ] #5 Decision recorded in task notes: keep settings.json if: "Bash(git commit *)" directive as documentation, or remove it once internal hook guard is in place — pick one and note why
<!-- AC:END -->
