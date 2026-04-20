---
id: TASK-27
title: Fix ralph-run sandbox bypass for distributable use
status: To Do
assignee: []
created_date: '2026-04-20 12:21'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-run skill uses 'nohup bash -c ./ralph.sh' which doesn't match the sandbox permission pattern 'Bash(nohup ./ralph.sh:*)'. Fix the skill to launch directly with 'nohup ./ralph.sh ... & disown' and restore the missing patterns in .claude/settings.local.json.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph-run skill launches with 'nohup ./ralph.sh ... & disown' instead of 'nohup bash -c'
- [ ] #2 .claude/settings.local.json includes Bash(./ralph.sh:*) and Bash(nohup ./ralph.sh:*)
- [ ] #3 ralph-run launches successfully without dangerouslyDisableSandbox
<!-- AC:END -->
