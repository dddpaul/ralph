---
id: TASK-80
title: Add TZ=Europe/Moscow date permission to settings.local.json template
status: Done
assignee: []
created_date: '2026-05-01 14:12'
updated_date: '2026-05-01 14:12'
labels:
  - permissions
  - cleanup
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Fresh-init projects prompt for permission on the timestamp conversion command from ralph-status Step 2.5: 'TZ=Europe/Moscow date -d ... || TZ=Europe/Moscow date -j -f ...'. Both fallback branches share the prefix 'TZ=Europe/Moscow date', so a single allow rule covers them. Add Bash(TZ=Europe/Moscow date:*) to skills/ralph-init/templates/settings.local.json so this prompt does not appear on freshly initialized projects.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/templates/settings.local.json contains 'Bash(TZ=Europe/Moscow date:*)' inside permissions.allow
- [x] #2 Template is still valid JSON
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added Bash(TZ=Europe/Moscow date:*) to template allow list. Single rule covers both fallback branches (GNU date -d and BSD date -j -f) since both share the prefix 'TZ=Europe/Moscow date'.

Commit: `4c8b800` - task-80: Add TZ=Europe/Moscow date permission to settings.local.json template
<!-- SECTION:NOTES:END -->
