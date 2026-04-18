---
id: TASK-9
title: Add Claude Code sandbox dependencies to devcontainer
status: To Do
assignee: []
created_date: '2026-04-18 12:17'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Claude Code inside the devcontainer warns about missing sandbox dependencies: bubblewrap (bwrap) and socat. Without these, commands run without sandboxing and filesystem/network restrictions are not enforced. Add both packages to the apt-get install list in .devcontainer/Dockerfile.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bubblewrap and socat added to apt-get install in .devcontainer/Dockerfile
- [ ] #2 Claude Code runs inside devcontainer without sandbox warning
- [ ] #3 All existing tests still pass
<!-- AC:END -->
