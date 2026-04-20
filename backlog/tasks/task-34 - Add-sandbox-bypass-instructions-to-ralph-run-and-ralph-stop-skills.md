---
id: TASK-34
title: Add sandbox bypass instructions to ralph-run and ralph-stop skills
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 15:59'
updated_date: '2026-04-20 16:05'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Several Bash commands in ralph-run and ralph-stop are blocked by Claude Code sandbox (kill, pkill, /tmp writes). Add 'dangerouslyDisableSandbox: true' instructions to all affected steps. ralph-run: kill -0 in precondition check (3.2), bash -n syntax check writing to /tmp (3.4), kill -0 post-launch verify (Step 4). ralph-stop: all kill/pkill commands (Steps 2-4).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-run skill has dangerouslyDisableSandbox instruction on Step 3.2 PID check
- [x] #2 ralph-run skill has dangerouslyDisableSandbox instruction on Step 3.4 syntax check (or uses $TMPDIR instead of /tmp)
- [x] #3 ralph-run skill has dangerouslyDisableSandbox instruction on post-launch kill -0 verify
- [x] #4 ralph-stop skill has dangerouslyDisableSandbox instruction on all kill/pkill commands
- [x] #5 No functional changes to ralph.sh itself
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add 'Use dangerouslyDisableSandbox: true for this Bash call' instructions to ralph-run (Step 3.2 kill -0 PID check, Step 3.4 bash -n /tmp write, Step 4 kill -0 post-launch verify) and ralph-stop (Steps 3, 5, 6 — all kill/pkill commands). No changes to ralph.sh itself.

Added dangerouslyDisableSandbox: true instructions to ralph-run SKILL.md (Steps 3.2, 3.4, 4) and ralph-stop SKILL.md (Steps 3, 5, 6). Files changed: ~/.claude/skills/ralph-run/SKILL.md, ~/.claude/skills/ralph-stop/SKILL.md. No changes to ralph.sh.
<!-- SECTION:NOTES:END -->
