---
id: TASK-218
title: >-
  One-time plugin version bump to publish merged TASK-215 and pending authoring
  artifacts
status: Done
assignee: []
created_date: '2026-08-02 08:21'
updated_date: '2026-08-02 08:23'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Mechanical publish task. The autonomous TASK-215 merge (9117ba7) changed shipped devcontainer template files but left the plugin version at 0.2.1, so the pre-push version-bump-guard blocks git push origin master. Bump both manifests 0.2.1 -> 0.2.2 (patch) to unblock, and commit the pending auto-version-bump design doc + rewritten TASK-217 file so the tree is clean before handing TASK-217 to Ralph. Legacy one-time step: the orchestrator that merged TASK-215 predated the auto-bump helper (TASK-217).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/.claude-plugin/plugin.json and .claude-plugin/marketplace.json both read version 0.2.2
- [x] #2 design/auto-version-bump-brainstorm.md and the rewritten task-217 file are committed on master
- [x] #3 version-bump-guard passes and git push origin master succeeds; origin tip contains the TASK-215 devcontainer change at version 0.2.2
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `ee0f412` - task-218: bump plugin version 0.2.1 -> 0.2.2 to publish the merged TASK-215 devcontainer change

Commit: `0f613c7` - task-218: publish auto-version-bump design and rewritten TASK-217 (helper feature)

Bumped both manifests 0.2.1 -> 0.2.2 (patch); committed the auto-version-bump design doc + rewritten TASK-217. Legacy one-time unblock for the pre-helper TASK-215 merge. Push verified separately.
<!-- SECTION:NOTES:END -->
