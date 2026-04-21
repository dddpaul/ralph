---
id: TASK-50
title: Add heartbeat file to ralph.sh for sandbox-friendly liveness check
status: To Do
assignee: []
created_date: '2026-04-21 15:17'
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
<!-- AC:END -->
