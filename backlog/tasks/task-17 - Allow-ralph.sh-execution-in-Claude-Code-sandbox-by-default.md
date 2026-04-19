---
id: TASK-17
title: Allow ralph.sh execution in Claude Code sandbox by default
status: To Do
assignee: []
created_date: '2026-04-19 08:30'
updated_date: '2026-04-19 09:17'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When Claude Code with sandbox enabled invokes ralph-run skill on the host, ralph.sh fails because mktemp uses system tmpdir, exec redirects use /dev/fd/N, and these aren't sandbox-allowed. Fix: add Bash permissions for ralph.sh execution to bypass sandbox for trusted command. Two changes: (1) .claude/settings.local.json in current project — add 'Bash(./ralph.sh:*)' and 'Bash(nohup ./ralph.sh:*)' to permissions.allow. (2) skills/ralph-init/templates/settings.local.json — same additions so future projects bootstrapped via ralph-init get this out of the box.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 .claude/settings.local.json permissions.allow includes 'Bash(./ralph.sh:*)' and 'Bash(nohup ./ralph.sh:*)'
- [ ] #2 skills/ralph-init/templates/settings.local.json permissions.allow includes the same two entries
- [ ] #3 Running ralph-run skill from Claude Code with sandbox enabled launches ralph.sh without permission errors
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Why sandbox blocks ralph.sh

When Claude Code runs any Bash() tool call with sandbox enabled, it wraps the entire command in bwrap (bubblewrap), creating a kernel-level mount namespace. All child processes inherit this namespace — spawning a new shell doesn't escape it.

ralph.sh fails inside bwrap because:
- mktemp writes to /tmp (not in sandbox allowlist)
- exec > >(tee -a ...) uses /dev/fd/N (restricted)
- Writes to backlog/.ralph-status.json and .ralph-run.log (restricted)

Fix: Add Bash(./ralph.sh:*) to permissions.allow so Claude Code skips bwrap for this specific trusted command. This is the most targeted approach vs disabling sandbox entirely.
<!-- SECTION:NOTES:END -->
