---
id: TASK-106
title: Update README Workflow with design/ paths and /ralph-review step
status: Done
assignee: []
created_date: '2026-05-08 19:06'
updated_date: '2026-05-08 19:32'
labels:
  - 'feature:ralph-review'
dependencies:
  - TASK-102
  - TASK-105
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reflect the new design/ convention and the new /ralph-review step in README.md Workflow section.

Changes:
1. Step 2 (Create a PRD): output path tasks/prd-[feature-name].md → design/[feature-name]-prd.md.
2. Step 3 (Convert PRD to backlog tasks): input path same change.
3. Add Step 5 — Cumulative review (recommended):
   /ralph-review name=<feature-name>
   Runs after Ralph completes the in-scope tasks. Reads design/<name>-prd.md and design/<name>-brainstorm.md, scores the bundle of completed tasks against the upstream intent. Writes design/<name>-review-<YYYY-MM-DD>.md.
4. Mention design/ as the canonical intent-doc folder somewhere near the Step 1 (Brainstorm) note.
5. If Step 1 (Brainstorm) section is appropriate, add a sentence: 'After the dialogue, save conclusions to design/<name>-brainstorm.md (the project brainstorm-rules.md will propose this).'

Out of scope: actual code changes for ralph-prd / ralph-backlog (TASK-102), ralph-reviewer agent (TASK-104), /ralph-review skill (TASK-105), migration logic (TASK-107).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README.md Workflow Step 2 references design/<name>-prd.md (not tasks/prd-...)
- [x] #2 README.md Workflow Step 3 references design/<name>-prd.md as input
- [x] #3 README.md Workflow contains a new Step 5 — Cumulative review (recommended) describing /ralph-review name=<name>
- [x] #4 README.md Workflow Step 1 (Brainstorm) mentions saving conclusions to design/<name>-brainstorm.md
- [x] #5 All workflow step numbers are sequential (1, 2, 3, 4, 5) with no gaps or duplicates
- [x] #6 No surviving references to the old tasks/prd-* path elsewhere in README.md
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Starting implementation. Will update README.md Workflow section with design/ paths and /ralph-review step.

Commit: `22548f8` - task-106: Update README Workflow with design/ paths and /ralph-review step

All AC verified. README Workflow updated: design/ paths in Steps 1-3, new Step 5 for /ralph-review.
<!-- SECTION:NOTES:END -->
