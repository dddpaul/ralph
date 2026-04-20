---
id: TASK-48
title: Align ralph-run skill defaults with ralph.sh defaults
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 20:12'
updated_date: '2026-04-20 20:37'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-run skill defaults differ from ralph.sh: effort (skill: max, ralph.sh: medium), timeout (skill: 60, ralph.sh: 15), devcontainer (skill: true, ralph.sh: false). These are intentional overrides for the skill use case but should be documented as such. Add a note in the skill explaining the defaults differ from ralph.sh CLI defaults and why.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-run skill documents that its defaults intentionally differ from ralph.sh CLI defaults
- [x] #2 Each differing default has a brief explanation why
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add a note section in the ralph-run SKILL.md explaining that the skill's defaults intentionally differ from ralph.sh CLI defaults, with per-parameter rationale. The three differences are: effort (max vs medium), timeout (60 vs 15), devcontainer (true vs false).

Commit: `ff5cfdf` - task-48: Document ralph-run skill default overrides vs ralph.sh CLI

Implemented: Added blockquote note in SKILL.md after the defaults table documenting that effort/timeout/devcontainer defaults intentionally differ from ralph.sh CLI, with per-parameter rationale. Files changed: skills/ralph-run/SKILL.md
<!-- SECTION:NOTES:END -->
