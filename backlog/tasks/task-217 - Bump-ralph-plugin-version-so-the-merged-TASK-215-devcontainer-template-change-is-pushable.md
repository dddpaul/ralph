---
id: TASK-217
title: Auto-bump plugin version on shipped-file changes (helper + lifecycle + tag)
status: Done
assignee: []
created_date: '2026-08-02 07:11'
updated_date: '2026-08-02 09:06'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Ralph is a Claude Code plugin marketplace: consumers run skills from an on-disk cache that `/plugin update` rebuilds ONLY when the plugin version increases. The TASK-214 pre-push `version-bump-guard.sh` therefore blocks a master push when shipped plugin files changed without a strictly-greater version. That guard is correct but the bump is manual, so every autonomous Ralph loop that touches a shipped file blocks at the GitHub push waiting for a human to bump — defeating fully-autonomous end-to-end runs (including loops driven from another orchestrator project).

This task adds a local, per-task **auto-bump helper** so the bump happens with no human in the loop.

## Approach (locked in brainstorm)

A shared `.claude/hooks/bump-version.sh` engine invoked as two explicit Task-Lifecycle Merge-step actions:
- `bump-version.sh --auto` (on the task branch, before merge): if `git diff --name-only master..HEAD` touches a shipped-set path, infer the increment (a newly-added skill dir `plugins/ralph/skills/<new>/` or agent file `plugins/ralph/agents/<new>.md` via `--diff-filter=A` -> minor; otherwise patch; major never auto), compute the target relative to LOCAL master's version, edit both `plugin.json` + `marketplace.json` to the same value, and commit with a branch-aware single-line message `task-N: bump plugin version to X.Y.Z (<increment>)`. No-op when no shipped change or when HEAD is already ahead of master (idempotent). `patch|minor|major` override inference; `--no-commit` stages only.
- `bump-version.sh --tag` (on master, after `git merge --no-ff`): read the version at HEAD; if no `vX.Y.Z` tag exists, create an annotated tag `git tag -a vX.Y.Z -m "ralph X.Y.Z"` on the MERGE COMMIT; else no-op.

Key decisions (rationale in the design doc):
- Compare against LOCAL master, not origin/master: the guard only needs one bump above origin and local master is always >= origin, so local comparison guarantees the guard passes with NO network fetch, no staleness, no concurrency handling, and per-task semantic increments.
- Explicit lifecycle step (not a pre-commit/pre-push hook): the proven Task Lifecycle is reliably followed; an unconditional `--auto` step (script self-no-ops) is hook-robust without auto-staging magic. Pre-push cannot auto-fix (push contents are computed before the hook runs).
- Tag the merge commit (post-merge), carried to origin via repo-local `git config push.followTags true` -- NO change to the generic orchestrator `push.py`.
- The `version-bump-guard.sh` stays byte-for-byte unchanged as the origin-based pre-push backstop: a bypassed/missed bump degrades to a visible block, never a silent stale-cache publish.
- Shared `is_shipped` predicate factored into a sourced snippet used by BOTH the guard and the helper so the shipped-set definition cannot drift.

## Files

- `.claude/hooks/bump-version.sh` (new) -- the engine (`--auto` / explicit increment / `--tag` / `--no-commit`).
- `.claude/hooks/lib/shipped-set.sh` (new) -- sourced `is_shipped` predicate.
- `.claude/hooks/version-bump-guard.sh` (exists) -- refactor to source the shared predicate; behavior preserved.
- `.git/hooks/post-commit` and/or its tracked source -- add the non-blocking interactive nudge.
- `CLAUDE.md` -- Task Lifecycle Merge step documents the two `bump-version.sh` actions in order.
- `tests/unit/bump-version.bats` (new) -- mirrors `tests/unit/version-bump-guard.bats`.

## Out of scope

- The one-time legacy bump that publishes the already-merged TASK-215 devcontainer change (a manual `0.2.1 -> 0.2.2` + push) -- done separately; the helper only covers changes going forward.
- Any change to the generic `push.py` or to non-devcontainer/host-process behavior.
- Distributing this tooling via ralph-init (it is repo-specific governance, like the guard -- no R11 parity, stays under `.claude/`).
- Mirroring the CLAUDE.md Merge-step addition into `plugins/ralph/skills/ralph-init/templates/` -- the version-bump governance is specific to THIS repo being a plugin marketplace; bootstrapped projects have no guard, so the CLAUDE.md change is repo-only and NO R11 template parity applies to it.
- Auto `major` bumps; distributed version/tag locking for truly-simultaneous racing pushes.

## Before starting (validation checklist)

1. `.claude/hooks/version-bump-guard.sh` and `tests/unit/version-bump-guard.bats` still exist (refactor + mirror targets).
2. Each AC is objectively pass/fail (file existence, grep, bats, git tag/log, ruff, pytest).
3. `.claude/` is in the guard's EXCLUDED set (so this task's own files do not require a version bump) -- confirm before relying on autonomous push.
4. No file is added under `plugins/ralph/` for this task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .claude/hooks/bump-version.sh exists, is executable, and supports the modes: --auto, an explicit patch|minor|major, --tag, and --no-commit
- [x] #2 .claude/hooks/lib/shipped-set.sh defines a sourced is_shipped predicate, and both version-bump-guard.sh and bump-version.sh source it (grep shows no duplicated inline shipped-set case-glob across the two)
- [x] #3 bump-version.sh --auto exits 0 without editing when git diff --name-only master..HEAD contains no shipped-set path
- [x] #4 bump-version.sh --auto infers minor when a newly-added (--diff-filter=A) skill dir under plugins/ralph/skills/ or agent file under plugins/ralph/agents/ is among the shipped changes, and patch otherwise; it never auto-selects major
- [x] #5 bump-version.sh --auto computes the target relative to local master version, is idempotent (no-op when HEAD is already ahead of master), and writes the same new version to both plugins/ralph/.claude-plugin/plugin.json and .claude-plugin/marketplace.json
- [x] #6 bump-version.sh --auto commits the bump with a single-line branch-aware message matching task-<N>: (accepted by the commit-prefix guard)
- [x] #7 bump-version.sh --tag creates an annotated tag vX.Y.Z on HEAD when absent and no-ops when the tag already exists, and repo-local git config push.followTags is true
- [x] #8 CLAUDE.md Task Lifecycle Merge step documents, in order, bump-version.sh --auto before merge and bump-version.sh --tag after merge on master
- [x] #9 The post-commit hook prints a non-blocking one-line nudge when a commit touched shipped files and the version is not yet ahead of master
- [x] #10 version-bump-guard.sh still blocks a push whose master..range changes shipped files without a strictly-greater version (behavior preserved after the is_shipped refactor)
- [x] #11 tests/unit/bump-version.bats covers no-op-no-shipped, patch inference, minor-on-new-skill, idempotent re-run, tag create+skip, and branch-aware commit message; uv run pytest, uv run ruff check ., and the full bats suite pass
- [x] #12 No file is added under plugins/ralph/ for this task (grep of the task diff is clean); all new tooling lives under .claude/ or tests/
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Factor is_shipped into .claude/hooks/lib/shipped-set.sh; source from version-bump-guard.sh (behavior-preserving) + new bump-version.sh. (2) Write .claude/hooks/bump-version.sh with modes --auto (infer patch|minor vs local master, idempotent, edits BOTH manifests via portable awk match/substr, branch-aware single-line commit), explicit patch|minor|major, --tag (annotated vX.Y.Z on HEAD + ensure push.followTags), --nudge (non-blocking post-commit reminder), --no-commit. cd to git toplevel; source lib via abs HOOK_DIR. (3) Wire --nudge into .git/hooks/post-commit (live hook only; template out of scope). (4) Set repo-local push.followTags=true. (5) CLAUDE.md Merge step: document --auto before merge, --tag after merge (live only; R11 template mirror explicitly out of scope per task). (6) tests/unit/bump-version.bats mirroring version-bump-guard.bats. Verify: uv run pytest, uv run ruff check ., full bats suite; grep confirms nothing under plugins/ralph/.

Commit: `0a551f2` - task-217: auto-bump plugin version on shipped-file changes (helper + shared shipped-set predicate + lifecycle + tests)

Implemented the auto-bump helper (Approach B, explicit lifecycle step). Files: .claude/hooks/lib/shipped-set.sh (new, shared is_shipped predicate), .claude/hooks/bump-version.sh (new, executable — modes --auto/patch|minor|major/--tag/--nudge/--no-commit), .claude/hooks/version-bump-guard.sh (refactored to source the shared predicate; behavior preserved — 7/7 guard bats still pass), CLAUDE.md (Merge step now documents --auto before merge + --tag after merge), tests/unit/bump-version.bats (new, 13 tests). Also (untracked, so not in the diff): live .git/hooks/post-commit gained a non-blocking '--nudge' call; repo-local 'git config push.followTags true' set. Key decisions: (1) compare against LOCAL master not origin (guard only needs one bump above origin; local master >= origin) — no network/staleness/concurrency; (2) portable in-place edit via awk match/substr (first 'version' only) — avoids GNU-only sed '0,/re/'; (3) target = master version + inferred increment (patch, or minor for a --diff-filter=A skill dir/agent file; major never auto); idempotent via already_ahead; (4) the post-commit nudge lives in .git/ (untracked) but its reusable logic is bump-version.sh --nudge, which IS in the diff and bats-tested (AC#9). R11: the CLAUDE.md Merge-step change is a deliberate one-sided change (NOT mirrored to ralph-init templates) — repo-specific plugin-marketplace governance; justified in the task Out-of-scope, satisfying R11's explicit carve-out. AC#12 clean: nothing under plugins/ralph/. Review: the lifecycle-mandated 'task-reviewer' subagent is not registered this session; substituted an independent 'claude' agent carrying the full task-reviewer charter (8-item checklist + R1-R16). Verdict APPROVED with full per-AC traceability. Verification: uv run ruff check . (clean), uv run pytest (346 passed), bats tests/unit (66 ok / 0 fail incl. 13 new), bats integration+e2e (58 ok / 0 fail). Live end-to-end demo (isolated throwaway repo): --auto patch 0.1.0->0.1.1 + branch-aware commit, --nudge silent post-bump, --auto idempotent no-op, --tag annotated v0.1.1 + push.followTags, and the live post-commit nudge firing on a shipped change.
<!-- SECTION:NOTES:END -->
