---
id: TASK-109
title: Allow writes to design/ folder on master branch
status: Done
assignee: []
created_date: '2026-05-08 21:15'
updated_date: '2026-05-08 21:24'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Master-branch-guard hook currently blocks all writes outside .claude/ and .gitignore. Design intent docs (PRDs, brainstorms, reviews) live in design/ and should be writable directly on master so /ralph-review can persist its output without forcing a task branch for every review.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 master-branch-guard.sh allows paths starting with design/ (or containing /design/) on master
- [x] #2 Both .claude/hooks/master-branch-guard.sh and skills/ralph-init/templates/claude/hooks/master-branch-guard.sh updated identically (template parity)
- [x] #3 Hook still blocks writes to other top-level paths on master (regression check: writing to README.md from master still denied)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `a3df2da` - task-109: Add design/ folder to master-branch-guard.sh exemption list (mirror in template copy)

Hook updated to allow design/ folder writes on master. Both live and template copies updated identically (R11 parity). Reviewer APPROVED.
<!-- SECTION:NOTES:END -->
