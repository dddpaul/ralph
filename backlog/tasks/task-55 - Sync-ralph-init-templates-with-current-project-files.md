---
id: TASK-55
title: Sync ralph-init templates with current project files
status: To Do
assignee: []
created_date: '2026-04-21 18:33'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Template CLAUDE.md still has remaster typos (lines 19, 20, 67). Template ralph.sh missing _is_heartbeat_fresh function, function comments, and updated double-run guard. Copy current CLAUDE.md and ralph.sh to skills/ralph-init/templates/.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Template CLAUDE.md has no remaster typos
- [ ] #2 Template ralph.sh matches current ralph.sh
- [ ] #3 Template post-commit hook matches current hook
<!-- AC:END -->
