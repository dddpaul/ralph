---
id: TASK-195
title: Update R11 template-parity paths
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 15:55'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-188
  - TASK-190
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Repoint the R11 parity rules to the relocated template location so parity stays enforceable. See design/ralph-marketplace-prd.md US-009.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .claude/task-reviewer-rules.md R11 paths reference plugins/ralph/skills/ralph-init/templates/...
- [x] #2 Both ralph.sh shim copies remain in the parity set and are documented as byte-identical (now carrying the resolver)
- [x] #3 R11 paths contain no stale top-level skills/ references
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Repoint R11 template-parity paths in .claude/task-reviewer-rules.md to the relocated plugins/ralph/ tree (post TASK-188 move, TASK-190 resolver). Edits scoped to R11 only (lines 98,102-110,112,120): (1) intro + 9-row parity table -> plugins/ralph/skills/ralph-init/templates/...; (2) ralph.sh note -> canonical at plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py, document shims now carry the 5-tier resolver and stay byte-identical; (3) agents exclusion note -> fix stale template path + drop stale top-level agents//skills/* distribution refs (now plugin-bundled). Legacy ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ resolver tier is a valid current ~/.claude path, not stale (PRD Non-Goals keeps tier 3). R5 (line 42) and R16 (lines 188,208) skills/ refs are outside R11 = out of scope.

Commit: `b23eca0` - task-195: Repoint R11 template-parity paths to plugins/ralph tree

Implemented in .claude/task-reviewer-rules.md R11 only (b23eca0): AC#1 intro + 9-row parity table + agents-note template path -> plugins/ralph/skills/ralph-init/templates/...; AC#2 ralph.sh note now documents both shims as byte-identical (diff empty, verified) and carrying the 5-tier resolver, canonical repointed to plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py; AC#3 verified zero stale top-level skills/ refs in R11 (all remaining skills/ occurrences are plugins/ralph/skills/...). Also removed the obsolete 'project-local skill' ralph-sync exclusion note: ralph-sync was deleted in TASK-194 (git ls-files confirms none tracked) and that note carried a stale top-level 'skills/' reference caught by AC#3 (repointing a deleted-skill note is meaningless; removal keeps R11 consistent per R12). Agents note reframed as plugin-bundled distribution (agents now at plugins/ralph/agents/, no top-level agents/). Out of scope (R11-only per ACs): R5 line and R16 lines still mention skills/ paths. Gate: uv run ruff check . PASS, uv run pytest 185 passed.

task-reviewer verdict: APPROVED (b23eca0, +13/-15, docs-only R11 change). All 3 AC verified against live repo; shims byte-identical; no stale top-level skills/ refs in R11. Non-blocking reviewer note: '5-tier' wording retained to stay consistent with the ralph.sh header, TASK-190, and PRD US-004 (tier 5 = clear-error path). Gate green: ruff clean, 185 pytest passed.
<!-- SECTION:NOTES:END -->
