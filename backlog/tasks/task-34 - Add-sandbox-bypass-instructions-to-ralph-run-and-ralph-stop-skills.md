---
id: TASK-34
title: Add sandbox bypass instructions to ralph-run and ralph-stop skills
status: To Do
assignee: []
created_date: '2026-04-20 15:59'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Several Bash commands in ralph-run and ralph-stop are blocked by Claude Code sandbox (kill, pkill, /tmp writes). Add 'dangerouslyDisableSandbox: true' instructions to all affected steps. ralph-run: kill -0 in precondition check (3.2), bash -n syntax check writing to /tmp (3.4), kill -0 post-launch verify (Step 4). ralph-stop: all kill/pkill commands (Steps 2-4).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph-run skill has dangerouslyDisableSandbox instruction on Step 3.2 PID check
- [ ] #2 ralph-run skill has dangerouslyDisableSandbox instruction on Step 3.4 syntax check (or uses $TMPDIR instead of /tmp)
- [ ] #3 ralph-run skill has dangerouslyDisableSandbox instruction on post-launch kill -0 verify
- [ ] #4 ralph-stop skill has dangerouslyDisableSandbox instruction on all kill/pkill commands
- [ ] #5 No functional changes to ralph.sh itself
<!-- AC:END -->
