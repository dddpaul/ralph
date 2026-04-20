---
id: TASK-48
title: Align ralph-run skill defaults with ralph.sh defaults
status: To Do
assignee: []
created_date: '2026-04-20 20:12'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-run skill defaults differ from ralph.sh: effort (skill: max, ralph.sh: medium), timeout (skill: 60, ralph.sh: 15), devcontainer (skill: true, ralph.sh: false). These are intentional overrides for the skill use case but should be documented as such. Add a note in the skill explaining the defaults differ from ralph.sh CLI defaults and why.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph-run skill documents that its defaults intentionally differ from ralph.sh CLI defaults
- [ ] #2 Each differing default has a brief explanation why
<!-- AC:END -->
