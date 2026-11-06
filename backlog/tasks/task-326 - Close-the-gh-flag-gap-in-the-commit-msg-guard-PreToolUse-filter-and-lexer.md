---
id: TASK-326
title: Close the gh flag gap in the commit-msg guard PreToolUse filter and lexer
status: In Progress
assignee: []
created_date: '2026-11-05T17:50:00Z'
updated_date: '2026-11-06T15:19:00Z'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
commit-msg-guard.sh is registered with if: Bash(gh pr create *) and its lexer's is_pr_create requires the words gh, pr, create in positions 0-2. gh accepts --repo/-R (a persistent flag) before or between the subcommands: gh -R owner/repo pr create and gh pr -R owner/repo create both parse (checked with --help). Such a PR body carrying a banned trailer reaches GitHub, and unlike commits there is no git-side commit-msg backstop for PR bodies. Found while doing TASK-325, which widened the git commit filters to Bash(git *) and kept gh out of scope because the fix needs a change to the shared lexer block.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 gh -R owner/repo pr create --body containing a banned trailer is denied by commit-msg-guard.sh (direct test and live test)
- [x] #2 gh pr -R owner/repo create with a banned trailer is denied (direct test)
- [x] #3 Non-PR gh commands (gh pr list, gh repo view) still produce no output from the guard
- [x] #4 The shared lexer block stays byte-identical in both guards and the live copies match the plugin (uv run pytest tests/python/test_commit_guards.py tests/python/test_plugin_hooks.py)
- [x] #5 .claude/settings.json and plugins/ralph/hooks/hooks.json carry the same widened gh filter
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add a skipopts helper to the shared lexer (skip leading -options, two-word for a given regex), reuse it in gitsub and a new is_pr_create that skips gh -R/--repo before and after pr; widen the gh filter to Bash(gh *) in .claude/settings.json and hooks.json; sync lexer into both guards and live copies; extend test_commit_guards.py and test_plugin_hooks.py (WIDENED_FILTERS).

Live test: 'false && gh -R owner/repo pr create --body <trailer>' was BLOCKED by the live hook in this session. Full pytest 1341 passed; ruff errors pre-existing (none in changed lines); bats not installed, shared-lexer equality checked by md5 of the marker block.
<!-- SECTION:NOTES:END -->
