---
id: TASK-79
title: Remove dead glob permission rules from settings.local.json template
status: Done
assignee: []
created_date: '2026-05-01 13:35'
updated_date: '2026-05-01 13:35'
labels:
  - cleanup
  - permissions
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bash(bash */preflight.sh:*) and Bash(bash */wait-heartbeat.sh:*) in skills/ralph-init/templates/settings.local.json never match at runtime. Claude Code permission patterns are literal-match with * as a suffix-only wildcard; * mid-pattern is not expanded as a glob. The rules that actually authorize these calls are the two $HOME-resolved entries merged in by Step 3.7 of the ralph-init skill. Delete the two dead glob entries from the template.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/templates/settings.local.json no longer contains 'Bash(bash */preflight.sh:*)' or 'Bash(bash */wait-heartbeat.sh:*)'
- [x] #2 Template is still valid JSON
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Removed two dead glob entries (Bash(bash */preflight.sh:*) and Bash(bash */wait-heartbeat.sh:*)) from skills/ralph-init/templates/settings.local.json. JSON re-validated with jq.
<!-- SECTION:NOTES:END -->
