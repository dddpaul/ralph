---
id: TASK-99
title: Add brainstorm step to README Workflow
status: Done
assignee: []
created_date: '2026-05-05 15:36'
updated_date: '2026-05-05 15:40'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
README Workflow currently shows PRD -> backlog -> run. Add a recommended Step 1 (Brainstorm) before Step 1 (Create a PRD), and renumber existing steps to 2/3/4. Brainstorm skill helps converge on architecture before writing PRD.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Workflow section has 4 numbered steps: Brainstorm, Create a PRD, Convert PRD to backlog tasks, Run Ralph
- [x] #2 Step 1 marked as (recommended), notes it can be skipped for trivial changes
- [x] #3 Existing Step 1/2/3 content is preserved verbatim under new numbers 2/3/4
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `c19e7e6` - task-99: Add Brainstorm step to README Workflow

task-reviewer APPROVED (commit c19e7e6). Inserted Step 1 (Brainstorm, recommended) with link to cc-thingz brainstorm plugin; renumbered existing steps to 2/3/4 with bodies preserved verbatim.
<!-- SECTION:NOTES:END -->
