---
id: TASK-190
title: Add orchestrator resolver to ralph.sh
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 11:36'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-188
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Give ralph.sh a 5-tier orchestrator resolver so a detached nohup launch finds the orchestrator wherever the plugin is installed (a detached shim has no CLAUDE_PLUGIN_ROOT). Precedence: 1 RALPH_ORCHESTRATOR env, 2 in-repo plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py, 3 legacy CLAUDE_CONFIG_DIR-or-HOME/.claude/skills/ralph-run/scripts, 4 glob newest ~/.claude/plugins/cache/*/ralph/*/.../ralph_orchestrator.py via sort -V and tail -1, 5 clear error. See design/ralph-marketplace-prd.md US-004.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Both ralph.sh shim copies (repo-root and ralph-init template) resolve the orchestrator via the 5-tier precedence in the PRD
- [x] #2 The two shim copies are byte-identical (diff produces no output)
- [x] #3 The ralph-init canonical-orchestrator gate checks whether the ralph plugin is installed instead of the fixed ~/.claude/skills path
- [x] #4 A bats test covers resolver tiers 2 and 4 and the missing-plugin error path
- [x] #5 bash -n ralph.sh passes and the script is R5-portable
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Rewrite both ralph.sh shim copies (repo-root + templates/root) with a 5-tier orchestrator resolver: (1) $RALPH_ORCHESTRATOR, (2) in-repo $RALPH_PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py, (3) legacy ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph_orchestrator.py, (4) newest plugin-cache glob ${cfg}/plugins/cache/*/ralph/*/skills/ralph-run/scripts/ralph_orchestrator.py via sort -V | tail -1, (5) clear error. Keep the two copies byte-identical. Update ralph-init Step 1 gate to check 'ralph plugin installed?' (plugin-cache glob) instead of the fixed ~/.claude/skills path. Rewrite tests/integration/shim.bats to cover AC#2 byte-identical + resolver tiers 2 & 4 + missing-plugin error via a stubbed uv on PATH. Verify bash -n, R5-portable, ruff, pytest 185, bats green.

Verification: bash -n passes on both shims; ruff clean; pytest 185/185 pass. New tests/integration/shim.bats: 4 tests (byte-identical shim parity + resolver tiers 2, 4, and missing-plugin error) all pass. Resolver validated manually across tiers 1/2/4/5; tier-4 test uses v0.9.0 vs v0.10.0 so it genuinely exercises sort -V (lexical sort would pick the wrong dir). Full recursive bats: 71 failures on this branch vs 72 on clean master — net -1 (my change fixed the old broken shim.bats and added zero regressions). The 71 pre-existing failures come from tests/helpers/common.bash:10 sourcing plugins/ralph/skills/ralph-run/scripts/ralph.sh, a bash orchestrator that TASK-188 replaced with ralph_orchestrator.py (Python); those obsolete bash unit/integration tests are superseded by the 185 pytest tests and are out of scope for TASK-190 (test-harness repoint is TASK-188/189 fallout). R11 shim-parity satisfied (diff empty); the R11 descriptive note about the exec target is updated by TASK-195 (US-009).

Commit: `741f846` - task-190: Add 5-tier orchestrator resolver to ralph.sh shim; ralph-init gate checks plugin installed; resolver-tier bats tests

Done: task-reviewer APPROVED (all 5 ACs, R5 portability, R11 shim-parity confirmed at blob level a2cc845). Final gate green: ruff clean, pytest 185/185, shim.bats 4/4, bash -n OK on both copies.
<!-- SECTION:NOTES:END -->
