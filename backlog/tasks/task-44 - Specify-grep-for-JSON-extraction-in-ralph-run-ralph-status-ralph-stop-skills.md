---
id: TASK-44
title: 'Specify grep for JSON extraction in ralph-run, ralph-status, ralph-stop skills'
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 16:49'
updated_date: '2026-04-20 19:50'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Skills say 'extract the pid field' from .ralph-status.json without specifying how. Claude sometimes uses python3 which may not be installed. Add explicit grep commands for JSON field extraction in all three skills. Example: grep -o '"pid":[0-9]*' file | grep -o '[0-9]*'. No python or jq dependency.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-status skill uses grep for extracting fields from .ralph-status.json
- [x] #2 ralph-run skill uses grep for PID extraction in precondition check
- [x] #3 ralph-stop skill uses grep for PID extraction
- [x] #4 No python3 or jq references in any ralph-* skill
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add explicit grep-based extraction commands for JSON fields in ralph-run (step 3.2), ralph-status (step 1), and ralph-stop (step 1). Use grep -o pattern for field extraction. Verify no python3/jq references exist.

Commit: `66bfb4c` - task-44: Specify grep for JSON extraction in ralph-run, ralph-status, ralph-stop skills

Implemented grep-based JSON extraction in all three ralph skills. Uses grep -o with regex patterns to extract fields from .ralph-status.json without python3/jq dependency.
<!-- SECTION:NOTES:END -->
