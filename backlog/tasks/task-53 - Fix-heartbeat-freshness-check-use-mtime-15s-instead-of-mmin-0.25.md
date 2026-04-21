---
id: TASK-53
title: 'Fix heartbeat freshness check: use -mtime -15s instead of -mmin -0.25'
status: Done
assignee:
  - '@claude'
created_date: '2026-04-21 17:19'
updated_date: '2026-04-21 17:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
BSD find on macOS truncates fractional -mmin values, making -mmin -0.25 always fail. Replace with -mtime -15s which works on macOS. For GNU find (Linux) use -newermt '15 seconds ago' as fallback. Update in: ralph.sh (double-run guard), ralph-status skill (Step 2), ralph-run skill (Steps 3.2 and 4).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Heartbeat check uses -mtime -15s on macOS
- [x] #2 Heartbeat check has GNU find fallback for Linux
- [x] #3 ralph.sh double-run guard updated
- [x] #4 ralph-status skill updated
- [x] #5 ralph-run skill updated
- [x] #6 All existing tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Use stat + arithmetic instead of find -mtime/-newermt. Portable: stat -f %m (macOS) || stat -c %Y (Linux) to get epoch mtime, then compare with date +%s. Add _is_heartbeat_fresh() function in ralph.sh.

Used stat -f %m (macOS) || stat -c %Y (Linux) + arithmetic instead of find -mmin. Added _is_heartbeat_fresh() function in ralph.sh. Updated ralph-status and ralph-run skills with inline stat check.
<!-- SECTION:NOTES:END -->
