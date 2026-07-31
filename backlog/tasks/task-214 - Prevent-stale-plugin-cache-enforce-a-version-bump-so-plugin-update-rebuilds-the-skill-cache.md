---
id: TASK-214
title: >-
  Prevent stale plugin cache: enforce a version bump so /plugin update rebuilds
  the skill cache
status: To Do
assignee: []
created_date: '2026-07-26 16:30'
updated_date: '2026-07-31 07:37'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Handoff. Source: /Users/paul/Private/Projects/ai/control-gateway@9b4d6dc544a2

## Why

Claude Code executes plugin skills from the on-disk cache at ~/.claude/plugins/cache/dddpaul-ralph/ralph/<version>/, which /plugin update rebuilds only when it detects a NEW version. The version is pinned at 0.1.0 in both manifests and never bumped, so update no-ops and the cache freezes while the dev repo, GitHub, and the marketplace advance. Real incident (2026-07-26): cached ralph-stop SKILL.md was ~a release behind — missing graceful-drain AND whole subsystems (ralph-refine, push.py, refine_orchestrator.py). Users silently ran stale skills. This makes cache refresh reliable by enforcing a version bump at the publish boundary.

## Locked design (from brainstorm)

BOUNDARY = push of master to origin (NOT per-commit). The version only matters when changes become pullable by consumers, i.e. when master reaches GitHub. Intermediate task commits, docs/config/backlog edits do NOT require a bump.

MECHANISM = a pre-push git hook, THIS-REPO-ONLY:
- Tracked guard script at .claude/hooks/version-bump-guard.sh (that dir is already tracked/un-ignored via '\!.claude/hooks/' in .gitignore). Reviewable + testable.
- Activation: .git/hooks/pre-push is a 2-line wrapper that execs the tracked script: exec "$(git rev-parse --show-toplevel)/.claude/hooks/version-bump-guard.sh" "$@". Standard hook location, so existing hooks keep working (no core.hooksPath migration). NOTE: nothing under .git/ can be committed (git special-cases it); the tracked SOURCE lives in .claude/hooks/, the .git/hooks/pre-push wrapper is installed once.
- pre-push receives '<local-ref> <local-sha> <remote-ref> <remote-sha>' on stdin. For the refs/heads/master line, diff remote-sha..local-sha (both local at push time — NO network).

RULE: if any shipped-set file changed in remote-sha..local-sha, require version at local-sha STRICTLY GREATER (sort -V, monotonic) than at remote-sha; else exit 1 with a BLOCKED message. Guard enforces monotonic-only, NOT a specific increment size.

SHIPPED SET: plugins/ralph/skills/**, plugins/ralph/agents/**, plugins/ralph/skills/ralph-run/scripts/**, plugins/ralph/.claude-plugin/plugin.json, .claude-plugin/marketplace.json. Excluded: README/design/backlog/.claude (docs & tooling, not shipped-and-executed).

PASS-THROUGH: non-master pushes; ranges touching no shipped-set file; first push (remote-sha all-zeros).

VERSION: bump BOTH manifests 0.1.0 -> 0.2.0 (equal) in this change — an honest minor catch-up for the features added since 0.1.0 (ralph-refine, push.py, resolver simplification), and it proves the refresh path. Going-forward discipline (documented, human convention — the guard only enforces monotonic): patch default (0.2.1, 0.2.2, ...) for fixes/in-skill edits; minor (0.3.0) for a new skill/agent/flag or removed/renamed skill; major deferred to a future 1.0 stable-surface declaration.

DISTRIBUTION: NONE. This guard is project-specific to the plugin-producer repo (seeded consumer projects have no manifests, so it is meaningless there). Do NOT add it to plugins/ralph/skills/ralph-init/templates/ and do NOT add an R11 parity row — same category as ralph-sync / task-reviewer-rules.

## Files

- plugins/ralph/.claude-plugin/plugin.json (exists) — version 0.1.0 -> 0.2.0.
- .claude-plugin/marketplace.json (exists) — metadata.version 0.1.0 -> 0.2.0.
- .claude/hooks/version-bump-guard.sh (to-create, tracked) — the guard.
- .git/hooks/pre-push (to-install, wrapper, not tracked) — execs the guard.
- bats test (to-create) under tests/ — exercises block/pass/docs-only.
- README.md and/or CLAUDE.md (exists) — release/refresh procedure + increment discipline.

## Out of scope

- Changing any skill behavior/logic (release plumbing only).
- Per-commit enforcement (boundary is push-of-master).
- CI/CD or external-registry publishing.
- ralph-init distribution / R11 parity for this guard.
- The ralph-stop graceful-drain verify (separate handoff TASK-213).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Cache-refresh trigger recorded in notes: /plugin update is version-gated (rebuilds cache off the version field), with evidence (marketplace/git advanced while cache stayed a frozen 0.1.0 snapshot)
- [ ] #2 Both manifests bumped 0.1.0 -> 0.2.0 and equal: plugins/ralph/.claude-plugin/plugin.json version and .claude-plugin/marketplace.json metadata.version
- [ ] #3 Tracked guard at .claude/hooks/version-bump-guard.sh plus a .git/hooks/pre-push wrapper that execs it (standard hook location, existing hooks unaffected)
- [ ] #4 On a push of refs/heads/master where shipped-set files (plugins/ralph/skills, agents, ralph-run/scripts, plugin.json, marketplace.json) changed in remote-sha..local-sha, the guard exits non-zero unless version at local-sha is strictly greater (sort -V) than at remote-sha
- [ ] #5 Guard exits 0 for: non-master pushes, ranges touching no shipped-set file (docs/design/backlog-only), and first push (remote-sha all-zeros)
- [ ] #6 A bats test exercises and passes all three cases: shipped-changed-without-bump -> non-zero, shipped-changed-with-bump -> zero, docs-only -> zero
- [ ] #7 Guard shell satisfies R5 GNU/BSD portability per .claude/task-reviewer-rules.md (no grep -P, no GNU-only flags)
- [ ] #8 Guard is project-specific: NOT added to plugins/ralph/skills/ralph-init/templates/ and NOT added to the R11 parity table
- [ ] #9 README.md or CLAUDE.md documents the release/refresh procedure (bump both manifests, commit, push, consumers run /plugin update) AND the increment discipline (patch default; minor for new skill/agent/flag; major deferred to 1.0), with the stale-cache warning
- [ ] #10 Lint green (uv run ruff check .) and tests green (uv run pytest)
<!-- AC:END -->
