---
id: TASK-296
title: Ship the Claude guard hooks as plugin hooks behind a marker gate
status: Done
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-04T15:47:00Z'
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
- [x] #1 The seven guards (commit-msg-guard, commit-prefix-guard, master-branch-guard, naming-guard, notes-guard, task-validator, filename-length-guard) live in plugins/ralph/hooks/
- [x] #2 plugins/ralph/hooks/hooks.json carries the 13 entries and if: filters of `plugins/ralph/skills/ralph-init/templates/claude/settings.json`, each running run.sh with the guard name under CLAUDE_PLUGIN_ROOT
- [x] #3 run.sh resolves the canonical git root from CLAUDE_PROJECT_DIR without crossing a nested repository and exits 0 unless .claude/ralph.json there has pluginHooks true
- [x] #4 run.sh exits 0 for a guard listed in localGuards, otherwise passes the hook input unchanged, keeps the guard exit code and exports RALPH_PROJECT_ROOT
- [x] #5 Guards use RALPH_PROJECT_ROOT for project paths and the payload cwd for command interpretation, and compute the root from CLAUDE_PROJECT_DIR when RALPH_PROJECT_ROOT is unset (tested by direct invocation)
- [x] #6 The managed template guard copies and this repo live managed guard copies stay byte-identical to the plugin, enforced by a parity test
- [x] #7 A project bootstrapped from the templates at this commit still blocks through its legacy guards (tested)
- [x] #8 Tests cover marker present and absent, localGuards, a subdirectory session, a nested repository, exit 2 passthrough and every hooks.json entry naming an existing executable
- [x] #9 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add plugins/ralph/hooks/{run.sh,hooks.json} plus copies of the 7 guards. run.sh resolves the root with git rev-parse --show-toplevel from CLAUDE_PROJECT_DIR (pwd -P), gates on .claude/ralph.json pluginHooks/localGuards via jq, cds to the payload cwd, exports RALPH_PROJECT_ROOT and pipes the input unchanged to the guard. hooks.json is generated from templates/claude/settings.json (same 13 entries and if: filters). task-validator and master-branch-guard take the root from RALPH_PROJECT_ROOT, else git toplevel of CLAUDE_PROJECT_DIR; mirror into templates and .claude/hooks. New pytest module covers parity, hooks.json fidelity, dispatcher cases and a template-bootstrapped legacy project.

Commit: `1edf197` - task-296: ship the Claude guard hooks as plugin hooks behind the ralph.json marker gate

Implemented: run.sh dispatcher + hooks.json generated from the template settings.json; guards copied into plugins/ralph/hooks. master-branch-guard and task-validator take the git root of RALPH_PROJECT_ROOT (dispatcher, or a ralph.sh shim that may sit in scripts/ralph/), else of CLAUDE_PROJECT_DIR. run.sh cds to the payload cwd so commit-prefix-guard reads the branch where the command ran. Added plugins/ralph/hooks/** to the shipped set (shipped-set.sh, README, doc-5). Checks: ruff clean, pytest 1098 passed/3 skipped, bats 205/206 — the one failure is R11 settings.local.json shape, which compares the gitignored local file this branch does not touch; bash -n on all changed shell files, test_bash32_syntax passes.

Review: task-reviewer APPROVED (score 8, 0 blocking). Minor 1: the hooks.json test compares only the first 13 entries — kept on purpose, because US-002 says later stories (US-022) may add entries. Minor 2: master-branch-guard now reads the branch from the project root, not from the cwd repo. So in legacy wiring too, an edit inside a nested repo under the project is judged by the outer repo's branch. This follows from AC5.

Commit: `a463eb9` - task-296: bump plugin version to 0.15.1 (patch)
<!-- SECTION:NOTES:END -->
