---
id: TASK-209
title: refine end-to-end test with fake-claude and green toolchain
status: To Do
assignee: []
created_date: '2026-07-22 16:29'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-205
  - TASK-206
  - TASK-207
  - TASK-208
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-009 of ralph-refine. Prove the port with a fake-LLM e2e test and a fully green toolchain, no real LLM call. See design/ralph-refine-prd.md US-009.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 test_refine_e2e.py uses a fake-claude stub (author emits <artifact>, reviewer emits SCORE: + <summary>) and asserts the loop converges, writes final.{type} + summary.md, and returns exit 0 at threshold
- [ ] #2 The reused tool/subprocess/devcontainer/signal layer gets no new tests (already covered)
- [ ] #3 uv run pytest passes with the new test_refine_* tests added
- [ ] #4 uv run ruff check . passes
- [ ] #5 pyright strict passes on ralph/refine/
<!-- AC:END -->
