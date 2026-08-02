---
id: TASK-217
title: Auto-bump plugin version on shipped-file changes (helper + lifecycle + tag)
status: To Do
assignee: []
created_date: '2026-08-02 07:11'
updated_date: '2026-08-02 08:21'
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
- [ ] #1 .claude/hooks/bump-version.sh exists, is executable, and supports the modes: --auto, an explicit patch|minor|major, --tag, and --no-commit
- [ ] #2 .claude/hooks/lib/shipped-set.sh defines a sourced is_shipped predicate, and both version-bump-guard.sh and bump-version.sh source it (grep shows no duplicated inline shipped-set case-glob across the two)
- [ ] #3 bump-version.sh --auto exits 0 without editing when git diff --name-only master..HEAD contains no shipped-set path
- [ ] #4 bump-version.sh --auto infers minor when a newly-added (--diff-filter=A) skill dir under plugins/ralph/skills/ or agent file under plugins/ralph/agents/ is among the shipped changes, and patch otherwise; it never auto-selects major
- [ ] #5 bump-version.sh --auto computes the target relative to local master version, is idempotent (no-op when HEAD is already ahead of master), and writes the same new version to both plugins/ralph/.claude-plugin/plugin.json and .claude-plugin/marketplace.json
- [ ] #6 bump-version.sh --auto commits the bump with a single-line branch-aware message matching task-<N>: (accepted by the commit-prefix guard)
- [ ] #7 bump-version.sh --tag creates an annotated tag vX.Y.Z on HEAD when absent and no-ops when the tag already exists, and repo-local git config push.followTags is true
- [ ] #8 CLAUDE.md Task Lifecycle Merge step documents, in order, bump-version.sh --auto before merge and bump-version.sh --tag after merge on master
- [ ] #9 The post-commit hook prints a non-blocking one-line nudge when a commit touched shipped files and the version is not yet ahead of master
- [ ] #10 version-bump-guard.sh still blocks a push whose master..range changes shipped files without a strictly-greater version (behavior preserved after the is_shipped refactor)
- [ ] #11 tests/unit/bump-version.bats covers no-op-no-shipped, patch inference, minor-on-new-skill, idempotent re-run, tag create+skip, and branch-aware commit message; uv run pytest, uv run ruff check ., and the full bats suite pass
- [ ] #12 No file is added under plugins/ralph/ for this task (grep of the task diff is clean); all new tooling lives under .claude/ or tests/
<!-- AC:END -->
