---
id: TASK-85
title: >-
  Remove dead glob permission rule for utc-to-moscow.sh from settings.local.json
  template
status: Done
assignee: []
created_date: '2026-05-01 18:22'
updated_date: '2026-05-01 18:47'
labels:
  - cleanup
  - permissions
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-84 introduced 'Bash(bash */utc-to-moscow.sh:*)' in skills/ralph-init/templates/settings.local.json. This is the same dead-code pattern TASK-79 cleaned up for preflight.sh and wait-heartbeat.sh: Claude Code permission patterns are literal-match with '*' as a SUFFIX-only wildcard. A '*' in the middle of the path is not expanded as a glob, so the rule never matches a real invocation like 'bash /Users/paul/.claude/skills/ralph-status/scripts/utc-to-moscow.sh ...'. The actually-working rule is the $HOME-resolved entry merged in by ralph-init Section 3.7. Delete the dead wildcard from the template.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/templates/settings.local.json no longer contains 'Bash(bash */utc-to-moscow.sh:*)'
- [x] #2 Template is still valid JSON
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Removed dead glob entry Bash(bash */utc-to-moscow.sh:*) from skills/ralph-init/templates/settings.local.json. JSON re-validated.
<!-- SECTION:NOTES:END -->
