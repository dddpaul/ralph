---
id: TASK-205
title: 'refine refinement loop, output structure, and summary'
status: Done
assignee: []
created_date: '2026-07-22 16:29'
updated_date: '2026-07-23 08:16'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-202
  - TASK-203
  - TASK-204
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-005 of ralph-refine. Run author->reviewer per iteration, stop at threshold or max, save every version, and reuse the ralph tool/devcontainer/signal layer. See design/ralph-refine-prd.md US-005 and doc-4 invariants.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Per iteration: run author -> save {output-dir}/artifact-vN.{type}; run reviewer -> save {output-dir}/review-vN.md; print iteration number and score
- [x] #2 Author/reviewer LLM calls go through the reused claude/opencode tool factory (tool.run(prompt, timeout_sec)) honoring --devcontainer, --model, --effort, --timeout
- [x] #3 Loop stops when score >= threshold: copies {output-dir}/final.{type}, writes {output-dir}/summary.md, exits 0
- [x] #4 Loop stops at max-iterations: warns, copies last artifact to final.{type}, writes summary.md, exits 1
- [x] #5 summary.md contains an iteration table (iteration, score, delta) plus final score / threshold / iteration count
- [x] #6 --on-error stop|continue|retry (with --retry-count) governs LLM-call failures (timeout exit code 124 or nonzero exit)
- [x] #7 --resume detects the last complete artifact-vN + review-vN pair, re-parses prior scores, and continues (or reports nothing-to-do when threshold already met or all iterations complete)
- [x] #8 --dry-run prints the iteration-1 prompts without any LLM call and exits 0
- [x] #9 --verbose prints composed prompts before each call
- [x] #10 SIGTERM/SIGINT during an LLM call cleans up the child process group via the reused signals.py on_spawn
- [x] #11 pytest covers threshold stop, max-iter stop, exit codes, on-error strategies, resume, and summary/delta in test_refine_loop.py
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan (US-005): add ralph/refine/summary.py (pure score/delta-table renderer) + ralph/refine/loop.py (self-contained loop reusing ralph.tools factory, ralph.devcontainer, ralph.signals via on_spawn; NO coupling to ralph.loop/tasks.py per FR-7). Wire cli.py to dispatch loop.run after validate. Per-iteration: author->save artifact-vN.{type}; reviewer->save review-vN.md (full transcript, for resume score/summary re-parse + author feedback); print 'Iteration N: score X/10'. Threshold>=->copy final.{type}+write summary.md+exit0; max-iter->warn+copy last+summary.md+exit1. --on-error stop|continue|retry(+retry-count) governs tool-exit(124/nonzero) AND extraction failures. --resume scans last complete artifact-vN+review-vN pair, re-parses all prior scores, continues or nothing-to-do. --dry-run prints iter-1 author prompt, exit0. --verbose prints composed prompts. Compact _SignalForwarder forwards SIGTERM to child pgid via on_spawn. --prompt/--draft: readable-file->contents else literal text. Tests: test_refine_loop.py (threshold/max-iter/exit codes/on-error/resume/summary+delta). Update US-002 test_cli_main_returns_0_on_valid_args to add --dry-run (cli.main now dispatches loop instead of stub-returning 0).

Commit: `3666f1f` - task-205: refine refinement loop, output structure, and summary (US-005)

Commit: `ab4970d` - task-205: wrap loop.py lines to 88-char style limit

Done (US-005). Added ralph/refine/loop.py (self-contained author->reviewer loop) + ralph/refine/summary.py (pure score/delta-table renderer); wired cli.py to dispatch loop.run after validate. Reuses ralph.tools factory (ClaudeTool/OpencodeTool via build_tool, timeout=args.timeout*60, on_spawn), ralph.devcontainer, ralph.signals extraction. Per iteration: author->artifact-vN.{type}; reviewer->review-vN.md (full transcript for resume score/summary re-parse + author feedback); prints 'Iteration N: score X/10'. Threshold>=->final.{type}+summary.md, exit 0; max-iter->warn+final+summary, exit 1. --on-error stop|continue|retry(+retry-count) governs BOTH tool-exit failures (124/nonzero) AND extraction failures uniformly. --resume scans last complete artifact-vN+review-vN pair, re-parses all prior scores, continues or reports nothing-to-do (threshold-met exit0 / all-iters-complete exit1). --dry-run prints iter-1 author prompt, exit0. --verbose prints composed prompts. Compact _SignalForwarder forwards SIGTERM to child pgid via on_spawn (self-contained, NOT importing ralph.loop, to honor FR-7 no-backlog-coupling). --prompt/--draft resolved leniently (readable file->contents else literal text). Updated one US-002 test (test_cli_main_returns_0_on_valid_args) to add --dry-run since cli.main now dispatches the loop. Gate: ruff clean, pyright strict 0 errors on ralph/refine/, pytest 314 passed (26 new in test_refine_loop.py). task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
