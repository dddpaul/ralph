---
id: TASK-214
title: >-
  Prevent stale plugin cache: enforce a version bump so /plugin update rebuilds
  the skill cache
status: To Do
assignee: []
created_date: '2026-07-26 16:30'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Claude Code loads and **executes** plugin skills from the on-disk CACHE at
`~/.claude/plugins/cache/dddpaul-ralph/ralph/<version>/`, NOT from the dev repo or the
marketplace checkout. That cache is a snapshot rebuilt only on plugin install/update, and
update appears to be **version-gated**: the plugin `version` is pinned at `0.1.0` in both
`plugins/ralph/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` and is
never bumped, so `/plugin update` no-ops and the cache freezes while the dev repo, GitHub
(`dddpaul/ralph.git`), and the marketplace checkout all advance together.

Consequence: users silently run outdated skills. Real incident (2026-07-26): the cached
`ralph-stop` SKILL.md was ~an entire release behind the marketplace — missing the
graceful-drain section AND whole subsystems (`ralph-refine`, `push.py`,
`refine_orchestrator.py`, updated `loop.py`/`args.py`). A `/ralph-stop` invocation
therefore executed stale instructions with no signal to the user. A manual
`rsync marketplace -> cache` fixed that machine, but that is a per-machine stopgap, not a
fix. For a plugin whose entire job is orchestrating autonomous work, silent skill
staleness is a correctness hazard.

Proposed solution: make the cache refresh reliable by (a) confirming the actual
refresh trigger, (b) adopting and **enforcing** a version-bump discipline so shipped
changes cannot land without a version change that consumers' `/plugin update` will pick
up, and (c) documenting the release/refresh procedure.

## Scope

In scope:
- Determine the real cache-refresh trigger: does `/plugin update` rebuild the cache off the
  `version` field, off git sha/content, or only on a full reinstall? Record the finding with
  evidence (e.g. marketplace advanced to a new sha while the cache stayed a frozen `0.1.0`
  snapshot).
- If `version` is the lever: bump it in BOTH `plugins/ralph/.claude-plugin/plugin.json`
  (`version`) and `.claude-plugin/marketplace.json` (`metadata.version`) off `0.1.0` as part
  of this change (proves the refresh path end-to-end).
- Add an ENFORCED guard: a committed script wired as a git hook (or an equivalent
  pytest/bats check) that FAILS a commit/push which modifies shipped plugin files
  (`plugins/ralph/skills/**`, `plugins/ralph/agents/**`, `plugins/ralph/skills/ralph-run/scripts/**`,
  and the two manifests) without a corresponding version bump, and PASSES for
  docs-only/no-op commits. Ship it with a test covering both the failing (changed, not
  bumped) and passing (bumped) cases.
- Document the release/refresh procedure (bump both manifests -> commit -> push ->
  consumers run `/plugin` update or reinstall to rebuild the cache) in README.md or CLAUDE.md,
  including the warning that skipping the bump leaves consumers on a stale cache.

Out of scope:
- Changing any skill's behavior/logic (this is release plumbing only).
- The ralph-stop graceful-drain verify/fix — that is the separate handoff TASK-213.
- Full CI/CD release automation or publishing to an external registry (a local guard +
  doc is enough; automation can be a follow-up).
- Modifying Claude Code's own cache/loader internals (not in this repo's control).

## Files

- `plugins/ralph/.claude-plugin/plugin.json` (exists) — holds `version` (currently `0.1.0`); one of the two to bump.
- `.claude-plugin/marketplace.json` (exists) — holds `metadata.version` (currently `0.1.0`); the other to bump.
- guard script + its test (to-create) — mirror the existing `*-guard.sh` shell-guard style under `plugins/ralph/skills/ralph-init/templates/claude/hooks/`, or a Python check under the ralph-run test suite; implementer chooses placement.
- `README.md` and/or `CLAUDE.md` (exists) — add the release/refresh procedure note.

## Source

Source: /Users/paul/Private/Projects/ai/control-gateway@9b4d6dc544a2
Related destination tasks (context, do NOT redo): TASK-187 (scaffold marketplace/plugin manifests), TASK-196 (marketplace docs), TASK-210 (documented graceful drain, Done), TASK-213 (verify graceful-drain guarantee).

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or observed behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in (do NOT touch skill logic; do NOT build CI publishing).

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The cache-refresh trigger is determined and recorded in the implementation notes: whether /plugin update rebuilds the cache off the version field, off git sha/content, or only on reinstall, with the supporting evidence
- [ ] #2 If version is the refresh lever: version is bumped off 0.1.0 in BOTH plugins/ralph/.claude-plugin/plugin.json (version) and .claude-plugin/marketplace.json (metadata.version) in this change, and the two values match
- [ ] #3 A committed guard (git-hook script or pytest/bats check) FAILS a commit/push that modifies shipped plugin files (plugins/ralph/skills, plugins/ralph/agents, plugins/ralph/skills/ralph-run/scripts, or the two manifests) without a version bump
- [ ] #4 The same guard PASSES for a docs-only or no-op commit that touches no shipped plugin files
- [ ] #5 An automated test (pytest or bats) exercises both the failing case (shipped file changed, version not bumped) and the passing case (version bumped), and both assertions pass
- [ ] #6 The guard shell code satisfies R5 GNU/BSD portability per .claude/task-reviewer-rules.md (no GNU-only flags)
- [ ] #7 README.md or CLAUDE.md documents the release/refresh procedure: bump both manifests, commit, push, and consumers run /plugin update or reinstall to rebuild the cache; with a warning that skipping the bump leaves a stale cache
- [ ] #8 Lint green: uv run ruff check .
- [ ] #9 Tests green: uv run pytest
<!-- AC:END -->
