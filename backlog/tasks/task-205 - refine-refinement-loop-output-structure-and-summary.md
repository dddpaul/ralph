---
id: TASK-205
title: 'refine refinement loop, output structure, and summary'
status: To Do
assignee: []
created_date: '2026-07-22 16:29'
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
- [ ] #1 Per iteration: run author -> save {output-dir}/artifact-vN.{type}; run reviewer -> save {output-dir}/review-vN.md; print iteration number and score
- [ ] #2 Author/reviewer LLM calls go through the reused claude/opencode tool factory (tool.run(prompt, timeout_sec)) honoring --devcontainer, --model, --effort, --timeout
- [ ] #3 Loop stops when score >= threshold: copies {output-dir}/final.{type}, writes {output-dir}/summary.md, exits 0
- [ ] #4 Loop stops at max-iterations: warns, copies last artifact to final.{type}, writes summary.md, exits 1
- [ ] #5 summary.md contains an iteration table (iteration, score, delta) plus final score / threshold / iteration count
- [ ] #6 --on-error stop|continue|retry (with --retry-count) governs LLM-call failures (timeout exit code 124 or nonzero exit)
- [ ] #7 --resume detects the last complete artifact-vN + review-vN pair, re-parses prior scores, and continues (or reports nothing-to-do when threshold already met or all iterations complete)
- [ ] #8 --dry-run prints the iteration-1 prompts without any LLM call and exits 0
- [ ] #9 --verbose prints composed prompts before each call
- [ ] #10 SIGTERM/SIGINT during an LLM call cleans up the child process group via the reused signals.py on_spawn
- [ ] #11 pytest covers threshold stop, max-iter stop, exit codes, on-error strategies, resume, and summary/delta in test_refine_loop.py
<!-- AC:END -->
