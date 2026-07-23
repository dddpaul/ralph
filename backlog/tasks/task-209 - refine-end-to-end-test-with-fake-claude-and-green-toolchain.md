---
id: TASK-209
title: refine end-to-end test with fake-claude and green toolchain
status: Done
assignee: []
created_date: '2026-07-22 16:29'
updated_date: '2026-07-23 09:07'
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
- [x] #1 test_refine_e2e.py uses a fake-claude stub (author emits <artifact>, reviewer emits SCORE: + <summary>) and asserts the loop converges, writes final.{type} + summary.md, and returns exit 0 at threshold
- [x] #2 The reused tool/subprocess/devcontainer/signal layer gets no new tests (already covered)
- [x] #3 uv run pytest passes with the new test_refine_* tests added
- [x] #4 uv run ruff check . passes
- [x] #5 pyright strict passes on ralph/refine/
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add e2e test proving the refine port converges with a fake LLM (no real call), plus keep the toolchain green.
- New fixture tests/fixtures/fake_refine_claude.py: a black-box 'claude' stand-in. Reads the composed prompt on stdin (parity with ClaudeTool -> _subprocess.execute), distinguishes author vs reviewer by the trailing ralph.refine.roles.REVIEW_INSTRUCTION (the contract roles.py exports for exactly this stub), emits <artifact> for author calls and a climbing 'SCORE: N' + <summary> for reviewer calls. Score sequence via FAKE_REFINE_SCORES; per-run counter files keyed off FAKE_REFINE_STATE (each claude call is a fresh process).
- New tests/test_refine_e2e.py: drives real refine_orchestrator.py as a subprocess (parity with test_e2e_fake_claude.py) with the shim on PATH; asserts convergence at threshold, artifact-vN/review-vN written, final.{type} == last artifact, summary.md content, exit 0. Parametrized over type md+puml to cover final.{type}. Backlog-independent (no backlog project needed).
- AC#2: no new tests for the reused tool/subprocess/devcontainer/signal layer (already covered) - the e2e exercises them for real, not via new unit tests.
- Green toolchain: uv run pytest, uv run ruff check ., pyright strict on scripts (test is fully typed).

Commit: `508e4b8` - task-209: add fake-claude e2e test proving the refine loop converges to threshold

Implemented US-009: fake-LLM e2e test + green toolchain (no real LLM call).
- tests/fixtures/fake_refine_claude.py: black-box 'claude' stand-in. Reads composed prompt on stdin (parity with ClaudeTool -> _subprocess.execute), distinguishes author vs reviewer by the trailing ralph.refine.roles.REVIEW_INSTRUCTION (imports the real exported constant so it keys on the live contract), emits <artifact> for author calls and a climbing 'SCORE: N' + <summary> for reviewer calls (scores via FAKE_REFINE_SCORES, indexed by per-run counter files derived from FAKE_REFINE_STATE since each call is a fresh process).
- tests/test_refine_e2e.py: drives real refine_orchestrator.py as a subprocess with the shim on PATH (parity with test_e2e_fake_claude.py). Asserts convergence at threshold (scores 6,7,9 -> iteration 3), artifact-vN/review-vN written, no over-run (artifact-v4 absent), final.{type} byte-equal to terminal artifact, summary.md table+result block, exit 0. Parametrized over md+puml to prove final.{type} is not hard-coded; plus a first-iteration convergence case. Backlog-independent (no backlog project needed).
- AC#2: no new unit tests for the reused tool/subprocess/devcontainer/signal layer; the e2e drives them for real.
- Toolchain: uv run pytest 317 passed, uv run ruff check . clean, uv run pyright strict 0 errors (covers ralph/refine/). task-reviewer agent verdict: APPROVED.
- Note: commit-prefix-guard.sh hook parses -m via line-based sed, so commit subjects must be single-line 'task-N: ...' (multi-line -m yields empty extraction -> blocked).
<!-- SECTION:NOTES:END -->
