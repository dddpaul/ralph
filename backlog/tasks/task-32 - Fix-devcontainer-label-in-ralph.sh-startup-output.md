---
id: TASK-32
title: Fix devcontainer label in ralph.sh startup output
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 13:52'
updated_date: '2026-04-20 14:14'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Line 450 uses ${USE_DEVCONTAINER:+ (devcontainer)} which prints (devcontainer) even when USE_DEVCONTAINER=false because the string 'false' is non-empty. Replace with a conditional that checks == true, matching lines 357 and 482.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph.sh startup message shows (devcontainer) only when --devcontainer flag is passed
- [x] #2 Startup message does NOT show (devcontainer) when running without --devcontainer
- [x] #3 Existing tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Replace ${USE_DEVCONTAINER:+ (devcontainer)} on line 450 with a conditional that checks == true, consistent with lines 357 and 482.

Commit: `a431148` - task-32: Fix devcontainer label conditional in startup output

Fixed by replacing ${USE_DEVCONTAINER:+ (devcontainer)} with conditional check == true, consistent with lines 357 and 483. Files changed: ralph.sh
<!-- SECTION:NOTES:END -->
