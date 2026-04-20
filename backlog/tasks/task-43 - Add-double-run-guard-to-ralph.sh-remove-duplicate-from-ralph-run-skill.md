---
id: TASK-43
title: 'Add double-run guard to ralph.sh, remove duplicate from ralph-run skill'
status: To Do
assignee: []
created_date: '2026-04-20 16:44'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add 5-line PID check to ralph.sh right before _update_status running: read .ralph-status.json, extract pid, kill -0, refuse if alive. Remove Step 3.2 (Ralph not already running) from ralph-run skill since ralph.sh now handles it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh refuses to start if PID from .ralph-status.json is alive
- [ ] #2 ralph-run skill Step 3.2 PID check is removed
- [ ] #3 Running ralph.sh twice produces clear error message
- [ ] #4 All existing tests pass
<!-- AC:END -->
