---
id: TASK-216
title: Bump plugin version to 0.2.1 for ralph-stop SKILL.md annotation
status: Done
assignee: []
created_date: '2026-08-01 09:31'
updated_date: '2026-08-01 09:33'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-213 changed a shipped skill file (plugins/ralph/skills/ralph-stop/SKILL.md — the verified graceful-drain annotation) without bumping the plugin version. The TASK-214 pre-push version-bump guard blocks a master push when shipped files change without a strictly-greater version, so /plugin update rebuilds the cache. Patch bump per the version discipline (doc annotation = patch).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/.claude-plugin/plugin.json version is 0.2.1
- [x] #2 \.claude-plugin/marketplace.json version is 0.2.1
- [x] #3 ruff clean and pytest green
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `ef7938b` - task-216: bump plugin version 0.2.0 -> 0.2.1 so /plugin update rebuilds the cache after the ralph-stop annotation

Bumped plugin.json + marketplace.json 0.2.0 -> 0.2.1. Diff is the two version strings only (jq-valid both). Ruff clean, pytest 346 passed. Heavyweight task-reviewer intentionally skipped: mechanical version-string bump with no logic to review; the underlying ralph-stop annotation (TASK-213) was already reviewed APPROVED. Purpose: satisfy the TASK-214 pre-push version-bump guard so /plugin update rebuilds the cache.
<!-- SECTION:NOTES:END -->
