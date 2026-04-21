---
id: TASK-53
title: 'Fix heartbeat freshness check: use -mtime -15s instead of -mmin -0.25'
status: To Do
assignee: []
created_date: '2026-04-21 17:19'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
BSD find on macOS truncates fractional -mmin values, making -mmin -0.25 always fail. Replace with -mtime -15s which works on macOS. For GNU find (Linux) use -newermt '15 seconds ago' as fallback. Update in: ralph.sh (double-run guard), ralph-status skill (Step 2), ralph-run skill (Steps 3.2 and 4).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Heartbeat check uses -mtime -15s on macOS
- [ ] #2 Heartbeat check has GNU find fallback for Linux
- [ ] #3 ralph.sh double-run guard updated
- [ ] #4 ralph-status skill updated
- [ ] #5 ralph-run skill updated
- [ ] #6 All existing tests pass
<!-- AC:END -->
