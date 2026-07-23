---
id: TASK-206
title: 'refine.sh root shim, R11 template parity, and init seeding'
status: Done
assignee: []
created_date: '2026-07-22 16:29'
updated_date: '2026-07-23 08:28'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-205
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-006 of ralph-refine. Add a repo-root refine.sh that resolves the installed plugin's refine_orchestrator.py, mirror it as an R11 template, and seed it via ralph-init. See design/ralph-refine-prd.md US-006 and doc-4 invariant 3.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Repo-root refine.sh mirrors ralph.sh's 5-tier resolver but resolves refine_orchestrator.py and execs uv run
- [x] #2 plugins/ralph/skills/ralph-init/templates/root/refine.sh exists and is byte-identical to the repo-root refine.sh (new R11 pair)
- [x] #3 ralph-init seeds refine.sh into a project root unconditionally, alongside ralph.sh
- [x] #4 .claude/task-reviewer-rules.md R11 table lists the refine.sh <-> templates/root/refine.sh pair
- [x] #5 bash -n on both refine.sh files passes; the shim satisfies R5 GNU/BSD portability
- [x] #6 Running ./refine.sh --help from the repo root prints usage (resolves the in-repo orchestrator via tier 2)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan (US-006): (1) Create repo-root refine.sh as a faithful mirror of ralph.sh's 5-tier resolver — tier-1 override REFINE_ORCHESTRATOR, tiers 2/3/4 resolve refine_orchestrator.py, exec 'uv run $ORCHESTRATOR'; keep RALPH_PROJECT_ROOT export + R5-portable idioms. (2) Copy byte-identical to plugins/ralph/skills/ralph-init/templates/root/refine.sh; chmod +x both. (3) ralph-init SKILL.md: seed refine.sh alongside ralph.sh in init (Step 3.1) + upgrade file-list/compare/overwrite/missing/display. (4) Add refine.sh<->templates/root/refine.sh row to R11 table in .claude/task-reviewer-rules.md and extend the ralph.sh note to cover refine.sh. (5) bash -n both + R5 check. (6) ./refine.sh --help prints usage via tier-2.

Commit: `3cdfa93` - task-206: add refine.sh root shim, R11 template parity, and init seeding

Done (US-006). Added repo-root refine.sh: faithful mirror of ralph.sh's 5-tier resolver (tier-1 override REFINE_ORCHESTRATOR, tiers 2/3/4 resolve refine_orchestrator.py, exec 'uv run $ORCHESTRATOR'), keeping RALPH_PROJECT_ROOT export and R5-portable idioms. Mirrored byte-identically to plugins/ralph/skills/ralph-init/templates/root/refine.sh (git blob a23ed1a, mode 100755, new R11 pair). ralph-init SKILL.md seeds refine.sh alongside ralph.sh across init (§3.1 + Files-created listing) and upgrade (file-check list, U3/U5 tables, details bullet, overwrite step); generic Missing-files rule covers a missing refine.sh. Added the refine.sh<->templates/root/refine.sh row to the R11 table and extended the shim note to state the two shims need not match each other, only their own template. Verified: bash -n both, ./refine.sh --help exits 0 printing usage via tier-2, ruff clean, 314 pytest pass. task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
