---
id: TASK-206
title: 'refine.sh root shim, R11 template parity, and init seeding'
status: To Do
assignee: []
created_date: '2026-07-22 16:29'
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
- [ ] #1 Repo-root refine.sh mirrors ralph.sh's 5-tier resolver but resolves refine_orchestrator.py and execs uv run
- [ ] #2 plugins/ralph/skills/ralph-init/templates/root/refine.sh exists and is byte-identical to the repo-root refine.sh (new R11 pair)
- [ ] #3 ralph-init seeds refine.sh into a project root unconditionally, alongside ralph.sh
- [ ] #4 .claude/task-reviewer-rules.md R11 table lists the refine.sh <-> templates/root/refine.sh pair
- [ ] #5 bash -n on both refine.sh files passes; the shim satisfies R5 GNU/BSD portability
- [ ] #6 Running ./refine.sh --help from the repo root prints usage (resolves the in-repo orchestrator via tier 2)
<!-- AC:END -->
