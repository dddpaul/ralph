---
id: TASK-2
title: Standardize branch name to main
status: Done
assignee:
  - '@claude'
created_date: '2026-04-16 07:52'
updated_date: '2026-04-17 08:04'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CLAUDE.md references master branch throughout but actual repo default branch is main. AGENTS.md correctly uses main. README also says 'merged to master'. Standardize all references to main.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All references to master in CLAUDE.md, README.md, and template CLAUDE.md are replaced with main
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Replace all 'master' branch references with 'main' in CLAUDE.md, skills/ralph-init/templates/CLAUDE.md, skills/ralph-init/SKILL.md, and README.md. The task file itself won't be edited directly.

Commit: `c1193a1` - task-2: Use main as default branch name in all docs

Replaced all master references with main in CLAUDE.md (5 occurrences), README.md (7 occurrences), skills/ralph-init/templates/CLAUDE.md (5 occurrences), skills/ralph-init/SKILL.md (1 occurrence). Pre-existing timeout test failures confirmed unrelated.
<!-- SECTION:NOTES:END -->
