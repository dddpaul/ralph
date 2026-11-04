---
id: TASK-296
title: Ship the Claude guard hooks as plugin hooks behind a marker gate
status: To Do
assignee: []
created_date: '2026-11-04T14:52:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Move the Claude guard hooks into the plugin, so that a guard change ships with a plugin update instead of a per-project upgrade.

Wiring:
- The plugin's hooks/hooks.json carries today's 13 entries and their if: filters.
- Every entry calls one dispatcher, run.sh <guard>. It acts only when the tracked marker .claude/ralph.json at the session's canonical git root has pluginHooks true, and skips guards listed in localGuards.
- The dispatcher exports RALPH_PROJECT_ROOT.

Keeping legacy projects working:
- Guards fall back to computing the root themselves when RALPH_PROJECT_ROOT is unset, because legacy projects call the guards directly.
- The template copies and this repo's live copies stay byte-identical to the plugin until US-007, and keep working in today's wiring.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-002 and FR-1, FR-4.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The seven guards (commit-msg-guard, commit-prefix-guard, master-branch-guard, naming-guard, notes-guard, task-validator, filename-length-guard) live in plugins/ralph/hooks/
- [ ] #2 plugins/ralph/hooks/hooks.json carries the 13 entries and if: filters of `plugins/ralph/skills/ralph-init/templates/claude/settings.json`, each running run.sh with the guard name under CLAUDE_PLUGIN_ROOT
- [ ] #3 run.sh resolves the canonical git root from CLAUDE_PROJECT_DIR without crossing a nested repository and exits 0 unless .claude/ralph.json there has pluginHooks true
- [ ] #4 run.sh exits 0 for a guard listed in localGuards, otherwise passes the hook input unchanged, keeps the guard exit code and exports RALPH_PROJECT_ROOT
- [ ] #5 Guards use RALPH_PROJECT_ROOT for project paths and the payload cwd for command interpretation, and compute the root from CLAUDE_PROJECT_DIR when RALPH_PROJECT_ROOT is unset (tested by direct invocation)
- [ ] #6 The managed template guard copies and this repo live managed guard copies stay byte-identical to the plugin, enforced by a parity test
- [ ] #7 A project bootstrapped from the templates at this commit still blocks through its legacy guards (tested)
- [ ] #8 Tests cover marker present and absent, localGuards, a subdirectory session, a nested repository, exit 2 passthrough and every hooks.json entry naming an existing executable
- [ ] #9 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
