---
id: TASK-178
title: 'Exclude __pycache__ from ralph-sync comparison to stop false [updated] churn'
status: Done
assignee: []
created_date: '2026-06-28 12:53'
updated_date: '2026-06-28 12:59'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The ralph-sync skill (.claude/skills/ralph-sync/sync.sh) classifies a skill as [updated] whenever its directory differs from the canonical ~/.claude copy. It compares with 'diff -rq "$src_dir" "$dst_dir"' (classify_skills, ~line 47; also the apply guard ~line 118 and the do_diff 'diff -ru' at ~lines 154/167). 'diff -r' recurses into __pycache__ and compares .cpython-*.pyc bytecode, which embeds mtimes/hashes and changes every time Python imports the package locally (e.g. the preflight/wait_heartbeat 'uv run python -m ralph.*' calls during /ralph-run). Result: skills/ralph-run perpetually shows [updated] after any local run, even though no source (.py / SKILL.md) changed — pure noise that masks real diffs and prompts pointless applies.

__pycache__/ is already in .gitignore (line 28) and no .pyc is tracked, so this is purely a sync-comparison hygiene fix, not a git issue.

Fix: add directory/file exclusions to the diff invocations in sync.sh so __pycache__ and *.pyc (and any .pyc) are ignored during comparison. 'diff' supports '-x <pattern>' / '--exclude=<pattern>' on BOTH GNU (Linux/devcontainer) and BSD (macOS) — R5-portable. Apply -x to: the classify_skills 'diff -rq' (~L47), the apply-path 'diff -rq' guard (~L118), and the do_diff 'diff -ru' (~L154 and ~L167) so the diff subcommand also hides pycache noise.

Example: diff -rq -x '__pycache__' -x '*.pyc' "$src_dir" "$dst_dir"

Scope: .claude/skills/ralph-sync/sync.sh ONLY. This skill is project-local (NOT distributed via ralph-init, NOT in the R11 mirror set), so it is a single-site change with no template parity obligation. Leave the cp -r apply as-is (copying pycache into canonical is harmless); the goal is only to stop the false [updated] classification.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All recursive diff calls in .claude/skills/ralph-sync/sync.sh (classify_skills diff -rq, the apply-path diff -rq guard, and both do_diff 'diff -ru' calls) pass -x '__pycache__' and -x '*.pyc'
- [x] #2 The exclusion flags use the portable 'diff -x <pattern>' form (works on both GNU and BSD diff per R5); no GNU-only long options that BSD diff rejects
- [x] #3 After regenerating bytecode locally (e.g. PYTHONPATH=$HOME/.claude/skills/ralph-run/scripts uv run --no-project python -m ralph.wait_heartbeat with no fresh heartbeat), 'bash .claude/skills/ralph-sync/sync.sh classify' reports skill ralph-run as [unchanged]
- [x] #4 bash -n .claude/skills/ralph-sync/sync.sh passes (no syntax error introduced)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add -x '__pycache__' -x '*.pyc' to all four recursive diff calls in .claude/skills/ralph-sync/sync.sh (classify_skills L47, apply-path L118 guard, do_diff agent L154, do_diff skill L167). Verify bytecode regeneration no longer triggers [updated] for ralph-run.

Commit: `820a8dd` - task-178: Exclude __pycache__/*.pyc from ralph-sync diff comparisons

task-reviewer APPROVED. Added portable '-x __pycache__ -x *.pyc' to all four recursive diff calls in .claude/skills/ralph-sync/sync.sh (L47 classify_skills, L118 apply-path guard, L154/L167 do_diff). Verified bash -n, ruff, pytest (185 pass), and live reproduction: divergent .pyc files no longer trigger [updated] for ralph-run.
<!-- SECTION:NOTES:END -->
