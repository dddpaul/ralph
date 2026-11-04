---
id: TASK-301
title: Switch ralph-init Init and Upgrade to the plugin-delivered files
status: To Do
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-04T15:20:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-300
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Switch ralph-init Init and Upgrade to the plugin-delivered files, and remove the template copies.

The parity rule applies: both Init and Upgrade change together.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-007.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Init runs migrate-plugin-hooks.sh tracked and clone and copies no guard scripts, no git hook bodies and no common allow rules
- [ ] #2 Upgrade runs tracked and clone and documents that a second host needs only clone after git pull
- [ ] #3 The template guard copies and the template git hook bodies are deleted, and the parity tests compare this repo live copies with the plugin instead
- [ ] #4 This repo keeps its legacy wiring and still passes its guards until the self-migration task
- [ ] #5 `plugins/ralph/skills/ralph-init/SKILL.md` covers both Init and Upgrade for the change, and `README.md` describes the marker, the switches, the shims and the one-time migration
- [ ] #6 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From the TASK-295 review: ralph-init SKILL.md's plugin-installed preflight (Step 1, the find over $CLAUDE_DIR/plugins/cache) still checks the cache by glob and does not check jq, while ralph.sh/refine.sh now resolve through installed_plugins.json with jq. Switch that check to the registry resolver (templates/shims/resolve-plugin.sh) when ralph-init moves to plugin-delivered files.
<!-- SECTION:NOTES:END -->
