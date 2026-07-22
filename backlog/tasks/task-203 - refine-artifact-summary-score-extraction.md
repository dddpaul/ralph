---
id: TASK-203
title: refine artifact/summary/score extraction
status: Done
assignee: []
created_date: '2026-07-22 16:29'
updated_date: '2026-07-22 17:11'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-201
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-003 of ralph-refine. Extract the author artifact and the reviewer score+summary from LLM output so iterations chain. Extractor reads ToolResult.stdout_path (combined stdout+stderr tee) and keys on the tag protocol. See design/ralph-refine-prd.md US-003.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 extract.artifact() returns the content between <artifact> and </artifact>; missing tags signal an error to the caller
- [x] #2 extract.summary() returns the content between <summary> and </summary>; missing tags signal an error to the caller
- [x] #3 extract.score() parses a line-anchored ^SCORE:\s*N validating N is an integer 1-10; missing or out-of-range signals an error
- [x] #4 Single-line tags (open+content+close on one line) are handled (parity with refine TASK-10)
- [x] #5 Leading blank lines inside tags are stripped (parity with refine TASK-12)
- [x] #6 On extraction failure the tee'd LLM stdout is surfaced for post-mortem (parity with refine TASK-16)
- [x] #7 Extraction reads from a ToolResult.stdout_path tee file and ignores noise outside the tag block
- [x] #8 pytest covers all above cases in test_refine_extract.py
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add ralph/refine/extract.py with three public extractors — artifact() / summary() / score() — each accepting a ToolResult (reads stdout_path tee), a Path, or a raw transcript str. Tag extraction uses non-greedy DOTALL regex so single-line tags (TASK-10 parity) and noise outside the block (AC#7) are handled; leading blank lines inside tags stripped (TASK-12 parity). score() matches line-anchored ^SCORE:\s*(\d+), takes the last match, validates 1-10. On any miss raise ExtractionError carrying the full tee'd transcript + source path for post-mortem (TASK-16 parity). Cover every branch in tests/test_refine_extract.py. Gate: uv run pytest + ruff + pyright strict on refine pkg.

Commit: `5a99365` - task-203: refine artifact/summary/score extraction (US-003)

Implemented ralph/refine/extract.py: artifact()/summary()/score() over a Source (ToolResult tee | Path | str). Non-greedy DOTALL tag regex handles single-line tags (TASK-10) and out-of-block noise (AC#7); _strip_leading_blank_lines drops leading whitespace-only lines (TASK-12) and rstrips, preserving internal blanks. score() = last line-anchored ^SCORE:\s*(\d+), validated 1-10. Failures raise ExtractionError carrying the full tee'd transcript + source path for post-mortem (TASK-16). 36 tests in test_refine_extract.py; full suite 269 passed, ruff + pyright(strict) clean. task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
