---
id: TASK-52
title: Add xhigh effort level to ralph.sh
status: To Do
assignee: []
created_date: '2026-04-21 17:07'
updated_date: '2026-04-21 17:08'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add xhigh as a valid effort level alongside low, medium, high, max. Update validation, --help text, and README. Check what claude CLI accepts for --effort and map xhigh appropriately.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh accepts --effort xhigh without error
- [ ] #2 Validation updated to include xhigh
- [ ] #3 --help output lists xhigh
- [ ] #4 All existing tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
xhigh is a new effort level for Claude Opus 4.7. It's a valid claude CLI --effort value. Also update the default MODEL from claude-opus-4-6 to claude-opus-4-7.
<!-- SECTION:NOTES:END -->
