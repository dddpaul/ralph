---
id: TASK-102
title: Establish design/ folder convention; update ralph-prd and ralph-backlog paths
status: To Do
assignee: []
created_date: '2026-05-08 19:05'
labels:
  - 'feature:ralph-review'
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Establish design/ as the canonical location for upstream-intent docs (PRDs, brainstorm summaries, cumulative reviews) instead of the current tasks/ folder, which collides semantically with backlog/tasks/. Naming uses the suffix style: design/<name>-prd.md, design/<name>-brainstorm.md, design/<name>-review-<date>.md. Feature slug <name> is the load-bearing identifier across brainstorm, PRD, backlog labels, and reviews.

Changes:
1. ralph-prd skill (skills/ralph-prd/SKILL.md): default output path tasks/prd-[feature-name].md → design/[feature-name]-prd.md. Update Output section, Filename rule, Example, and 'Next Step' reference at the bottom.
2. ralph-backlog skill (skills/ralph-backlog/SKILL.md): default PRD input path tasks/prd-*.md → design/*-prd.md. Add label 'feature:<name>' to every backlog task it creates (slug derived from PRD filename: strip 'design/' prefix and '-prd.md' suffix). Update Output Format and Example sections to show -l feature:<name>.
3. Both skills updated in this repo AND user-global copies refreshed via ralph-sync after merge.

Out of scope (separate tasks): brainstorm save handoff, ralph-reviewer agent, /ralph-review skill, README, migration prompt.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 skills/ralph-prd/SKILL.md writes to design/<name>-prd.md (suffix style); all 5 references updated (Output section, Filename, Example, Next Step text, Checklist)
- [ ] #2 skills/ralph-backlog/SKILL.md reads PRD from design/<name>-prd.md (suffix style); Conversion Rules and Example reflect new path
- [ ] #3 skills/ralph-backlog/SKILL.md mandates -l feature:<name> on every backlog task create command, with <name> derived from PRD filename
- [ ] #4 Example block in ralph-backlog SKILL.md updated to show feature:<name> label on each backlog task create
- [ ] #5 Bash syntax of any inline backlog task create examples in the SKILL.md is valid (bash -n where applicable)
- [ ] #6 Both SKILL.md files pass markdown logical consistency (no dangling references to old tasks/ path)
<!-- AC:END -->
