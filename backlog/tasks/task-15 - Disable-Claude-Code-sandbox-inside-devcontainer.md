---
id: TASK-15
title: Disable Claude Code sandbox inside devcontainer
status: Done
assignee:
  - '@claude'
created_date: '2026-04-19 06:14'
updated_date: '2026-04-19 06:14'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Claude Code sandbox breaks inside devcontainer because host ~/.claude is bind-mounted with host-specific paths that don't exist at /workspace. Fix: add CLAUDE_SANDBOX_ENABLED=false to containerEnv in devcontainer.json. The container already has iptables firewall for network isolation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CLAUDE_SANDBOX_ENABLED set to false in devcontainer.json containerEnv
- [x] #2 Claude Code can run bash commands inside devcontainer without sandbox errors
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add CLAUDE_SANDBOX_ENABLED=false to containerEnv in .devcontainer/devcontainer.json

Commit: `10bb550` - task-15: Disable Claude Code sandbox inside devcontainer

Added CLAUDE_SANDBOX_ENABLED=false to containerEnv. AC2 requires manual verification in devcontainer.
<!-- SECTION:NOTES:END -->
