---
id: TASK-207
title: 'Port refine example role sets (article, drawio, plantuml)'
status: To Do
assignee: []
created_date: '2026-07-22 16:29'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-205
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-007 of ralph-refine. Port the three example author/reviewer/prompt role sets verbatim from ~/dev/ai/refine/examples/ into the skill so refine runs out of the box. See design/ralph-refine-prd.md US-007.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 skills/ralph-refine/examples/article/{author,reviewer,prompt}.md present
- [ ] #2 skills/ralph-refine/examples/drawio/{author,reviewer,prompt}.md present (drawio reviewer references the arch-draw skill)
- [ ] #3 skills/ralph-refine/examples/plantuml/{author,reviewer,prompt}.md present
- [ ] #4 Each reviewer role contains the SCORE: N (1-10) output instruction and the <summary> protocol; each author role documents the <artifact> protocol
- [ ] #5 Content matches the source ~/dev/ai/refine/examples/ sets
<!-- AC:END -->
