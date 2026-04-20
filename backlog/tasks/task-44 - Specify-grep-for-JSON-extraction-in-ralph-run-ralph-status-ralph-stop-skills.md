---
id: TASK-44
title: 'Specify grep for JSON extraction in ralph-run, ralph-status, ralph-stop skills'
status: To Do
assignee: []
created_date: '2026-04-20 16:49'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Skills say 'extract the pid field' from .ralph-status.json without specifying how. Claude sometimes uses python3 which may not be installed. Add explicit grep commands for JSON field extraction in all three skills. Example: grep -o '"pid":[0-9]*' file | grep -o '[0-9]*'. No python or jq dependency.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph-status skill uses grep for extracting fields from .ralph-status.json
- [ ] #2 ralph-run skill uses grep for PID extraction in precondition check
- [ ] #3 ralph-stop skill uses grep for PID extraction
- [ ] #4 No python3 or jq references in any ralph-* skill
<!-- AC:END -->
