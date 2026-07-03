---
id: TASK-197
title: Verify devcontainer plugin-cache reachability
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 16:16'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-190
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ensure the plugin is reachable inside the devcontainer so resolver tier 4 works there. See design/ralph-marketplace-prd.md US-011.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 It is confirmed that ~/.claude/plugins is available inside the container under CLAUDE_CONFIG_DIR=/home/node/.claude (mount verified, or added in .devcontainer/devcontainer.json and the template)
- [x] #2 A documented smoke test shows the ralph.sh resolver finding the orchestrator from inside the container
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: verify the plugins bind mount reaches CLAUDE_CONFIG_DIR inside the container (AC#1) and add a documented, reproducible smoke test proving the ralph.sh resolver finds the orchestrator via tier 4 from inside the container (AC#2).

AC#1 (mount verified — no change needed): .devcontainer/devcontainer.json and its ralph-init template (byte-identical, diff empty) already carry 'source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind', which bind-mounts the WHOLE host ~/.claude (including plugins/cache/) onto CLAUDE_CONFIG_DIR=/home/node/.claude. Verified live inside the container: 'ls -d $CLAUDE_CONFIG_DIR/plugins/cache' -> /home/node/.claude/plugins/cache. The plugins/ subtree is covered by the existing whole-directory bind, so no new mount was added.

AC#2 (documented smoke test): added 'Devcontainer plugin-cache reachability' subsection to README.md with a 2-step smoke test. Captured output (run inside container):
  Step 1 (mount): /home/node/.claude/plugins/cache
  Step 2 (resolver tier 4): RESOLVED=<tmp>/cfg/plugins/cache/dddpaul-ralph/ralph/v1.0.0/skills/ralph-run/scripts/ralph_orchestrator.py
Step 2 uses a scratch config dir + scratch shim copy (tier 2 skipped) + stub uv, mirroring what '/plugin install' lays in the cache; deterministic so it passes whether or not the real plugin is installed. Also documented a real-install confirmation command.

Key decisions: documented smoke test in README (not a new committed script) to avoid extra R5/portability + maintenance surface; the resolver mechanism is already unit-tested by tests/integration/shim.bats tier-4 case, so the README's unique value is the devcontainer mount+resolver combination. README is outside the R11 parity set, so no template mirror required; devcontainer.json unchanged so no parity impact.

Verification: uv run ruff check . = All checks passed; uv run pytest = 185 passed; bats tests/integration/shim.bats = 4/4 ok.

Commit: `0e1a448` - task-197: document devcontainer plugin-cache reachability smoke test

task-reviewer verdict: APPROVED. Both ACs satisfied; AC#1 mount verified (no devcontainer change needed), AC#2 documented smoke test in README verified verbatim inside container. R5/R11/R12 clean. Final gate: ruff clean, pytest 185 passed, shim.bats 4/4.
<!-- SECTION:NOTES:END -->
