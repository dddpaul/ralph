---
id: TASK-203
title: refine artifact/summary/score extraction
status: To Do
assignee: []
created_date: '2026-07-22 16:29'
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
- [ ] #1 extract.artifact() returns the content between <artifact> and </artifact>; missing tags signal an error to the caller
- [ ] #2 extract.summary() returns the content between <summary> and </summary>; missing tags signal an error to the caller
- [ ] #3 extract.score() parses a line-anchored ^SCORE:\s*N validating N is an integer 1-10; missing or out-of-range signals an error
- [ ] #4 Single-line tags (open+content+close on one line) are handled (parity with refine TASK-10)
- [ ] #5 Leading blank lines inside tags are stripped (parity with refine TASK-12)
- [ ] #6 On extraction failure the tee'd LLM stdout is surfaced for post-mortem (parity with refine TASK-16)
- [ ] #7 Extraction reads from a ToolResult.stdout_path tee file and ignores noise outside the tag block
- [ ] #8 pytest covers all above cases in test_refine_extract.py
<!-- AC:END -->
