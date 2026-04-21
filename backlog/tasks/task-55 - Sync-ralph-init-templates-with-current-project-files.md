---
id: TASK-55
title: Sync ralph-init templates with current project files
status: Done
assignee:
  - '@claude'
created_date: '2026-04-21 18:33'
updated_date: '2026-04-21 18:40'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Template CLAUDE.md still has remaster typos (lines 19, 20, 67). Template ralph.sh missing _is_heartbeat_fresh function, function comments, and updated double-run guard. Copy current CLAUDE.md and ralph.sh to skills/ralph-init/templates/.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Template CLAUDE.md has no remaster typos
- [x] #2 Template ralph.sh matches current ralph.sh
- [x] #3 Template post-commit hook matches current hook
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Copy current CLAUDE.md to template CLAUDE.md, preserving the template's Project-Specific placeholder section. (2) Copy current ralph.sh to template ralph.sh. (3) Post-commit hook already matches — verify only.

Commit: `5e777d8` - task-55: Sync ralph-init templates with current project files

Synced template CLAUDE.md (fixed 3 remaster typos) and template ralph.sh (added _is_heartbeat_fresh, function comments, heartbeat subprocess, improved double-run guard). Post-commit hook already matched. Files: skills/ralph-init/templates/CLAUDE.md, skills/ralph-init/templates/ralph.sh
<!-- SECTION:NOTES:END -->
