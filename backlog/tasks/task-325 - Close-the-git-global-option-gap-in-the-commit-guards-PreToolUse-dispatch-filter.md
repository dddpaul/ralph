---
id: TASK-325
title: >-
  Close the git global-option gap in the commit guards' PreToolUse dispatch
  filter
status: In Progress
assignee: []
created_date: '2026-11-05T17:43:00Z'
updated_date: '2026-11-05T17:54:00Z'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
commit-msg-guard.sh and commit-prefix-guard.sh are registered in .claude/settings.json with if: Bash(git commit *) (and gh pr create * for the trailer guard). That filter requires the command to literally start with the string "git commit ". A git global option before the subcommand -- git -c key=value commit, git -C dir commit, --git-dir=, --work-tree=, --namespace=, --config-env= -- breaks that literal prefix, so the harness never even runs the guard script for that invocation shape. Confirmed live in this session: 'git -c user.name=test -c user.email=test@test commit --allow-empty -m "no prefix at all"' committed on a task-N branch with no PreToolUse denial at all (no hookSpecificOutput, no deny) -- the hook plainly did not fire. This is a dispatch-layer gap, separate from and in addition to the guard scripts' own internal lexer, which (tests/python/test_commit_guards.py::test_msg_guard_denies_real_commit already covers 'git -C /tmp commit ...') correctly denies these shapes once invoked directly -- proving the scripts are fine and the registration is the hole.

Originally flagged by claude-mac (Mac host, from a TASK-302 review) as the git -c key=value case specifically; broadened here to the general git-global-option class since the root cause (literal-prefix if: match) covers all of them identically.

A related, now-superseded finding: an untracked mycloud TASK-91 handoff file in this working tree (backlog/tasks/task-294 - Close-two-prefix-guard-bypasses-left-by-the-TASK-281-lexer.md) described two different bypasses in the OLD bash/awk lexer (an ANSI-C $'...' message, and only-the-first-commit-in-a-chain being checked). Both are already fixed in the current jq-lexer implementation (task-281's 'merge upstream's TASK-281 implementation' + task-292's hardening) -- verified directly against .claude/hooks/commit-prefix-guard.sh in a scratch repo: both shapes are now correctly denied. That file's content is stale and out of scope for this task; it is being left alone pending a separate decision on deleting it.

The asymmetry from that same analysis still applies and motivates fixing the prefix guard specifically: the trailer policy has the git-side commit-msg hook template as a backstop (a trailer that slips the PreToolUse guard still cannot land), but nothing else enforces the task-N: prefix, so a dispatch hole here is a hole in the whole prefix policy.

Likely fix shape: broaden the if: pattern (e.g. Bash(git *) / Bash(gh *)) and rely on each script's own existing fast-path case statement (case "$cmd" in *git*commit*) and the is_commit/gitsub lexer logic) to stay precise and cheap for non-commit invocations -- rather than trying to enumerate every global-option spelling in the if: pattern itself.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 git -c user.name=x -c user.email=y commit -m "no prefix" on a task-N branch is denied by commit-prefix-guard.sh (live test, not just the script invoked directly)
- [x] #2 git -C . commit -m "no prefix" on a task-N branch is denied by commit-prefix-guard.sh (live test)
- [x] #3 The equivalent trailer-bearing command (a git -c ... commit carrying a banned Co-Authored-By trailer) is denied by commit-msg-guard.sh (live test)
- [x] #4 All canonical cases still pass after the change: plain unprefixed commit denied, correctly task-N: -prefixed commit allowed, ANSI-C $'...' unprefixed commit denied, a chained command whose second commit lacks the prefix denied (uv run pytest tests/python/test_commit_guards.py)
- [x] #5 This repo's .claude/settings.json and the ralph-init template settings.json stay byte-identical for the changed if: entries (R11 template parity)
- [x] #6 bash -n on both changed hook scripts passes and the shared infra portability rules (GNU/BSD, bash 3.2) are satisfied
- [x] #7 The decision on whether to also widen the gh pr create * filter for an analogous global-option gap is made and recorded in the task notes, even if the decision is 'out of scope, filed separately'
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: widen the two commit-guard filters from Bash(git commit *) to Bash(git *) in .claude/settings.json and plugins/ralph/hooks/hooks.json (the plugin hooks.json replaced the old ralph-init template settings.json, so it is the R11 parity target). Keep the legacy fixture as the record of what old ralph-init wrote, and map the widened filter in the hooks.json parity test. Rely on each guard's fast-path case plus the lexer's is_commit check for non-commit git commands. Add direct tests for git -c/-C/--git-dir/--work-tree commits, ANSI-C and chained commits, and non-commit git commands, then live-test in this session.

gh pr create decision (AC #7): not widened. gh has no global options that can come before the subcommand (--repo/-R are per-command flags placed after pr create; only --help/--version are top-level and do nothing), so Bash(gh pr create *) has no analogous gap. Env-prefixed shapes (GH_REPO=x gh pr create, env git commit) fall under the harness's own permission-rule matching rather than the git global-option class and are out of scope; no follow-up filed.

Correction to the gh decision above: gh does accept the persistent --repo/-R flag before or between the subcommands (gh -R a/b pr create and gh pr -R a/b create both parse, checked with --help), so Bash(gh pr create *) has an analogous gap, and PR bodies have no git-side backstop. Closing it needs a change to the shared lexer (is_pr_create matches gh pr create word by word) as well as the filter, so it is out of scope here and filed as TASK-326.
<!-- SECTION:NOTES:END -->
