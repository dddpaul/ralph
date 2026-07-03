---
id: TASK-187
title: Scaffold marketplace and plugin manifests
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 10:25'
labels:
  - 'feature:ralph-marketplace'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the marketplace and plugin manifest files so Claude Code recognizes this repo as an installable marketplace shipping one ralph plugin. Marketplace name: dddpaul-ralph. See design/ralph-marketplace-prd.md US-001.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .claude-plugin/marketplace.json exists, names marketplace dddpaul-ralph, and lists one plugin ralph with source ./plugins/ralph
- [x] #2 plugins/ralph/.claude-plugin/plugin.json exists with name ralph, a semver version, description, author, homepage, repository, and license
- [x] #3 Both manifest files are valid JSON (jq . on each exits 0)
- [x] #4 uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: US-001 scaffolding. Create (1) .claude-plugin/marketplace.json — name=dddpaul-ralph, owner, one plugin ralph source=./plugins/ralph; (2) plugins/ralph/.claude-plugin/plugin.json — name=ralph, version=0.1.0 (semver), description, author(object), homepage+repository=https://github.com/dddpaul/ralph, license=MIT. Validate both with jq . (exit 0). Run uv run ruff check . Schema per Claude Code plugin marketplace spec (marketplace: name/owner/plugins[]; plugin: name/version/description/author/homepage/repository/license).

Commit: `a279a69` - task-187: Scaffold dddpaul-ralph marketplace and ralph plugin manifests

Implemented US-001 scaffolding. Created .claude-plugin/marketplace.json (name=dddpaul-ralph, owner dddpaul, one plugin ralph, source=./plugins/ralph) and plugins/ralph/.claude-plugin/plugin.json (name=ralph, version=0.1.0, description, author object, homepage+repository=https://github.com/dddpaul/ralph, license=MIT). Both validate under jq (exit 0); ruff passes; 185 pytest tests still green (no regression). task-reviewer APPROVED. No skills/agents moved yet — deferred to TASK-188.
<!-- SECTION:NOTES:END -->
