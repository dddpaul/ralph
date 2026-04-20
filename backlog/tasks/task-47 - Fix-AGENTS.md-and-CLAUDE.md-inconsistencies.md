---
id: TASK-47
title: Fix AGENTS.md and CLAUDE.md inconsistencies
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 20:12'
updated_date: '2026-04-20 20:35'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
AGENTS.md line 52 says task-<id> but correct format is task-<id>-description per CLAUDE.md. CLAUDE.md has 3 typos: remaster should be remain (lines 19, 20) and return to (line 67).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AGENTS.md branch naming matches CLAUDE.md: task-<id>-description
- [x] #2 CLAUDE.md remaster typos fixed to remain/return to
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Fix AGENTS.md line 52 branch naming from task-<id> to task-<id>-description. Fix CLAUDE.md lines 19, 20 remaster→remain and line 67 remaster→return to.

Commit: `831fd48` - task-47: Consistent branch naming and typo fixes in docs

Fixed AGENTS.md branch naming from task-<id> to task-<id>-description. Fixed three typos in CLAUDE.md: remaster→remain (lines 19,20) and remaster→return to (line 67).
<!-- SECTION:NOTES:END -->
