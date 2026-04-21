---
id: TASK-50
title: Add heartbeat file to ralph.sh for sandbox-friendly liveness check
status: To Do
assignee: []
created_date: '2026-04-21 15:17'
updated_date: '2026-04-21 16:28'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add background heartbeat loop to ralph.sh that touches backlog/.ralph-heartbeat every 5s. Heartbeat child checks parent alive via kill -0 $$ and exits on parent death (handles SIGKILL). ralph-status skill uses find -mmin -0.25 to check freshness instead of kill -0 PID, eliminating dangerouslyDisableSandbox requirement. Remove dangerouslyDisableSandbox instruction from ralph-status Step 2. Add .ralph-heartbeat to .gitignore.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh starts background heartbeat loop touching backlog/.ralph-heartbeat every 5s
- [ ] #2 Heartbeat child exits when parent dies (kill -0 check inside loop)
- [ ] #3 EXIT trap kills heartbeat process and removes file
- [ ] #4 ralph-status uses find -mmin for liveness, no kill -0 or dangerouslyDisableSandbox
- [ ] #5 backlog/.ralph-heartbeat in .gitignore
- [ ] #6 All existing tests pass
- [ ] #7 ralph-run Step 3.2 uses heartbeat freshness instead of kill -0
- [ ] #8 ralph-run Step 4 post-launch verify uses heartbeat instead of kill -0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation details:

ralph.sh changes:
- HEARTBEAT="$PROJECT_DIR/backlog/.ralph-heartbeat"
- Spawn heartbeat: _ralph_pid=$$ ; (while kill -0 "$_ralph_pid" 2>/dev/null; do touch "$HEARTBEAT"; sleep 5; done) &
- Store HB_PID=$\! for cleanup
- Add to existing EXIT trap: kill $HB_PID 2>/dev/null; rm -f "$HEARTBEAT"
- Place after mkdir -p backlog, before _update_status running

ralph-status skill changes (SKILL.md Step 2):
- Replace kill -0 with: find "$HEARTBEAT" -mmin -0.25 -print 2>/dev/null | grep -q .
- Remove dangerouslyDisableSandbox instruction from Step 2
- If heartbeat fresh AND state==running → alive
- If heartbeat stale AND state==running → re-read status file (may have completed), if still running → crashed
- If state==completed/failed → skip heartbeat check, trust file

ralph-stop skill: keep dangerouslyDisableSandbox on kill/pkill commands (those still need it)

Also update ralph-run skill:
- Step 3.2 (already running check): replace kill -0 with heartbeat freshness check: find backlog/.ralph-heartbeat -mmin -0.25. If fresh → ralph is running, refuse to start. Remove dangerouslyDisableSandbox from this step.
- Step 4 (post-launch verify): replace kill -0 $RALPH_PID with heartbeat check. Wait 3-5s for first heartbeat to appear, then check freshness. Remove dangerouslyDisableSandbox from this step.
<!-- SECTION:NOTES:END -->
