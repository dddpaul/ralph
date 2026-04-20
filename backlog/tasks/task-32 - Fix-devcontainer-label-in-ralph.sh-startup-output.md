---
id: TASK-32
title: Fix devcontainer label in ralph.sh startup output
status: To Do
assignee: []
created_date: '2026-04-20 13:52'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Line 450 uses ${USE_DEVCONTAINER:+ (devcontainer)} which prints (devcontainer) even when USE_DEVCONTAINER=false because the string 'false' is non-empty. Replace with a conditional that checks == true, matching lines 357 and 482.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh startup message shows (devcontainer) only when --devcontainer flag is passed
- [ ] #2 Startup message does NOT show (devcontainer) when running without --devcontainer
- [ ] #3 Existing tests pass
<!-- AC:END -->
