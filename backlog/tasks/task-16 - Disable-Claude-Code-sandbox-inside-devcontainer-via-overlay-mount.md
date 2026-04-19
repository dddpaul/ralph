---
id: TASK-16
title: Disable Claude Code sandbox inside devcontainer via overlay mount
status: Done
assignee:
  - '@claude'
created_date: '2026-04-19 06:38'
updated_date: '2026-04-19 06:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Claude Code sandbox breaks inside devcontainer because bubblewrap can't create user namespaces. The settings file is bind-mounted from host so can't be modified directly. Fix: use mount --bind overlay to patch sandbox.enabled=false inside the container without affecting host. Created init-claude.sh script, added SYS_ADMIN capability, updated Dockerfile and postStartCommand.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 init-claude.sh patches settings.local.json sandbox.enabled to false via mount --bind overlay
- [ ] #2 Host settings.local.json remains unchanged
- [ ] #3 Claude Code can run bash commands inside devcontainer
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Replaces TASK-15 env var approach which didn't work. Uses mount --bind overlay instead.
<!-- SECTION:NOTES:END -->
