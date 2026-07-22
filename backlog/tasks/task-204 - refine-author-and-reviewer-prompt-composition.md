---
id: TASK-204
title: refine author and reviewer prompt composition
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
US-004 of ralph-refine. Compose author and reviewer prompts from role files plus prior context so each LLM call has the right inputs and output-format instructions. See design/ralph-refine-prd.md US-004.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Author iteration 1 with --prompt: role text + task prompt
- [ ] #2 Author iteration 1 with --draft: role text + draft content
- [ ] #3 Author iteration >1: role text + previous artifact + previous full review
- [ ] #4 Author prompt appends the instruction to wrap output in <artifact>...</artifact>
- [ ] #5 Reviewer prompt: role text + current artifact + previous <summary> when iteration >1
- [ ] #6 Reviewer prompt appends the instruction to emit SCORE: N and <summary>...</summary>
- [ ] #7 pytest covers each composition path in test_refine_roles.py
<!-- AC:END -->
