---
id: TASK-108
title: Save ralph-review brainstorm conclusions to design/ralph-review-brainstorm.md
status: Done
assignee: []
created_date: '2026-05-08 19:07'
updated_date: '2026-05-08 19:08'
labels:
  - 'feature:ralph-review'
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Capture the conversational design for the ralph-review feature in the canonical location, following the structure that TASK-103 will codify in .claude/brainstorm-rules.md. Produces the working example of the convention the rule will mandate.

This task pre-creates the design/ folder and the first brainstorm doc (the bootstrap case: brainstorm doc for the very feature that introduces design/ folder).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 design/ralph-review-brainstorm.md exists with sections: Architecture decision, Components/flows, Scope cuts, Open questions, Hand-off
- [x] #2 Architecture decision summarizes the ralph-review skill + ralph-reviewer agent split (intent-vs-implementation lens distinct from per-task task-reviewer)
- [x] #3 Components/flows lists the 5-pass rubric (PRD coverage, non-goal protection, brainstorm scope cuts, success-metric realism, out-of-scope creep)
- [x] #4 Scope cuts records: numeric scoring rejected (3-bucket verdict instead), no auto-trigger after Ralph (manual /ralph-review only), no PRD↔task explicit linkage in ralph-backlog (uses feature:<name> label instead)
- [x] #5 Hand-off section names TASK-102 through TASK-107 as the implementation tasks
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Wrote design/ralph-review-brainstorm.md following the structure that TASK-103 will codify. Bootstrap case — first inhabitant of design/.
<!-- SECTION:NOTES:END -->
