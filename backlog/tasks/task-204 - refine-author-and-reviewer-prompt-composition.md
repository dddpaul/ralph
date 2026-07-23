---
id: TASK-204
title: refine author and reviewer prompt composition
status: Done
assignee: []
created_date: '2026-07-22 16:29'
updated_date: '2026-07-23 07:48'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-201
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-004 of ralph-refine. Compose author and reviewer prompts from role files plus prior context so each LLM call has the right inputs and output-format instructions. See design/ralph-refine-prd.md US-004.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Author iteration 1 with --prompt: role text + task prompt
- [x] #2 Author iteration 1 with --draft: role text + draft content
- [x] #3 Author iteration >1: role text + previous artifact + previous full review
- [x] #4 Author prompt appends the instruction to wrap output in <artifact>...</artifact>
- [x] #5 Reviewer prompt: role text + current artifact + previous <summary> when iteration >1
- [x] #6 Reviewer prompt appends the instruction to emit SCORE: N and <summary>...</summary>
- [x] #7 pytest covers each composition path in test_refine_roles.py
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan (US-004 prompt composition): Add ralph/refine/roles.py as a PURE string-composition module (mirrors prompts.py — no file I/O; the loop reads files and passes content). Public API: (1) author_prompt(role, *, task=None, draft=None, previous_artifact=None, previous_review=None) -> str — iter-1 seed path (task XOR draft, AC#1/#2) vs continuation path (previous_artifact+previous_review, AC#3), ValueError on incoherent combos; always appends ARTIFACT_INSTRUCTION containing '<artifact>...</artifact>' (AC#4). (2) reviewer_prompt(role, artifact, *, previous_summary=None) -> str — role+artifact, plus previous summary when iter>1 (AC#5); appends REVIEW_INSTRUCTION containing 'SCORE: N' + '<summary>...</summary>' (AC#6). Export ARTIFACT_INSTRUCTION/REVIEW_INSTRUCTION constants (shared contract w/ extract.py tag protocol, example roles US-007, e2e stub US-009). Sections joined by blank lines with '## Header' labels; role leads, instruction last. Tests: test_refine_roles.py covers all 5 composition paths + appended instructions + validation errors + ordering (AC#7). Gate: uv run ruff check . / pyright strict on refine/ / pytest — all green (verified baseline 269 passing).

Commit: `8556967` - task-204: compose author and reviewer prompts from role files (US-004)

Implemented ralph/refine/roles.py (US-004): pure author_prompt()/reviewer_prompt() string builders + exported ARTIFACT_INSTRUCTION/REVIEW_INSTRUCTION constants. Design: pure composition (no file I/O — mirrors prompts.py/args.py/extract.py; the US-005 loop reads role/seed files and passes content), so every path is directly unit-testable. author_prompt branches seed (task XOR draft, iter 1) vs continuation (previous_artifact+previous_review, iter>1) with ValueError guards on incoherent combos; reviewer_prompt adds the prior <summary> only when supplied (iter>1). Sections use '## Header' labels joined by blank lines; role leads, output-protocol instruction is the final block. Instruction constants pin the same tag protocol extract.py keys on (<artifact>...</artifact>, line-anchored SCORE: N 1-10, <summary>...</summary>) — shared contract for US-007 example roles and US-009 e2e stub. Tests: test_refine_roles.py, 23 cases covering all 5 composition paths, both appended instructions, block ordering, whitespace trimming, and all 4 guard permutations. Gate all green: ruff clean, pyright strict 0 errors, pytest 292 passed (+23). task-reviewer agent: APPROVED. Files: scripts/ralph/refine/roles.py, tests/test_refine_roles.py.
<!-- SECTION:NOTES:END -->
