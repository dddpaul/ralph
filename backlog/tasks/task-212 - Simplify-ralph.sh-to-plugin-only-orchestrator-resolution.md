---
id: TASK-212
title: Simplify ralph.sh to plugin-only orchestrator resolution
status: Done
assignee: []
created_date: '2026-07-25 13:40'
updated_date: '2026-07-25 14:17'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Collapse the 5-tier orchestrator resolver in ralph.sh to tier 1 ($RALPH_ORCHESTRATOR explicit override) plus tier 4 (newest installed marketplace plugin-cache orchestrator) plus a clear install-the-plugin error. Drop tier 2 (in-repo plugin source) and tier 3 (legacy ~/.claude/skills install). Keep the detached-run behaviour and the final exec uv run "$ORCHESTRATOR" "$@".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph.sh resolves the orchestrator only via $RALPH_ORCHESTRATOR or the newest installed plugin-cache orchestrator
- [x] #2 The in-repo-source and legacy ~/.claude/skills resolution tiers are removed
- [x] #3 ralph.sh exits with a clear install-the-plugin error when no orchestrator is found
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Rewrite ralph.sh resolver — keep tier 1 ($RALPH_ORCHESTRATOR) + newest plugin-cache tier + clear install error; drop in-repo-source and legacy ~/.claude/skills tiers; update header comment. (2) Mirror byte-identical to templates/root/ralph.sh (R11). (3) shim.bats: remove tier-2 test, fix stale in-repo comments in tier-4/tier-5 tests + file header. (4) Fix ralph.sh-specific stale docs: README resolver+devcontainer section, ralph-init SKILL.md lines 66/115, R11 note in task-reviewer-rules.md (note ralph.sh now differs from refine.sh which stays 5-tier). Leave refine.sh untouched (out of scope). Verify: bash -n both shims + diff parity + uv run pytest + ruff + bats shim.bats.

Commit: `031f0e0` - task-212: simplify ralph.sh resolver to override + plugin-cache only

Done. ralph.sh resolver collapsed to tier 1 ($RALPH_ORCHESTRATOR override) + newest plugin-cache tier + clear install-the-plugin error; in-repo-source and legacy ~/.claude/skills tiers removed. Both shim copies byte-identical (R11). shim.bats renumbered (1=override, 2=cache, 3=error) + added a tier-1 override test and negative tests for the two dropped tiers. common.bash setup_test_dir switched from the removed legacy tier (CLAUDE_CONFIG_DIR trick) to the tier-1 RALPH_ORCHESTRATOR override so integration/e2e tests that run 'bash ralph.sh' keep resolving the in-tree orchestrator. Docs refreshed: README (shim + devcontainer), ralph-init SKILL.md, ralph-refine SKILL.md (dropped now-false 'mirroring ralph.sh'), R11 note documents ralph.sh vs refine.sh asymmetry (refine.sh intentionally stays 5-tier). Verify: ruff clean; pytest 346; bats integration 52/52, e2e 6/6, shim 6/6; unit 3 failures (11/12/27) pre-existing + env-specific (fail on clean master). task-reviewer: APPROVED. Commit 031f0e0.
<!-- SECTION:NOTES:END -->
