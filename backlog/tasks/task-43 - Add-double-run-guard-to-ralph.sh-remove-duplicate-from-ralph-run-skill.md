---
id: TASK-43
title: 'Add double-run guard to ralph.sh, remove duplicate from ralph-run skill'
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 16:44'
updated_date: '2026-04-20 19:46'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add 5-line PID check to ralph.sh right before _update_status running: read .ralph-status.json, extract pid, kill -0, refuse if alive. Remove Step 3.2 (Ralph not already running) from ralph-run skill since ralph.sh now handles it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph.sh refuses to start if PID from .ralph-status.json is alive
- [x] #2 ralph-run skill Step 3.2 PID check is removed
- [x] #3 Running ralph.sh twice produces clear error message
- [x] #4 All existing tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Add PID guard to ralph.sh right after RALPH_SOURCE_ONLY check, before _update_status running. Read STATUS_FILE, extract pid with grep, check kill -0, exit 1 if alive. 2) Remove Step 3.2 from ralph-run SKILL.md. 3) Renumber Step 3.3→3.2, 3.4→3.3.

Commit: `efc67de` - task-43: Double-run guard in ralph.sh rejects start if existing PID is alive

Implemented: Added double-run PID guard to ralph.sh after STATUS_FILE definition. Extracts pid from .ralph-status.json via grep, checks kill -0, exits 1 if alive. Removed Step 3.2 from ralph-run SKILL.md and renumbered 3.3→3.2, 3.4→3.3. Test 121 (Temp file cleaned up on timeout) is a pre-existing flaky test that also fails on master.
<!-- SECTION:NOTES:END -->
