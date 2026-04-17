---
id: TASK-4
title: Fix devcontainer timezone conflict
status: To Do
assignee: []
created_date: '2026-04-16 07:52'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
.devcontainer/devcontainer.json has America/Los_Angeles as build arg default but hardcodes Europe/Moscow in containerEnv. These conflict — containerEnv overrides the build arg.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Timezone configuration is consistent — containerEnv uses the same source as the build arg
<!-- AC:END -->
