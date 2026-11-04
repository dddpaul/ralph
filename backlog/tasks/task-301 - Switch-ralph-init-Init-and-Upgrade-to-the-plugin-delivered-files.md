---
id: TASK-301
title: Switch ralph-init Init and Upgrade to the plugin-delivered files
status: Done
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-04T18:44:00Z'
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
- [x] #1 Init runs migrate-plugin-hooks.sh tracked and clone and copies no guard scripts, no git hook bodies and no common allow rules
- [x] #2 Upgrade runs tracked and clone and documents that a second host needs only clone after git pull
- [x] #3 The template guard copies and the template git hook bodies are deleted, and the parity tests compare this repo live copies with the plugin instead
- [x] #4 This repo keeps its legacy wiring and still passes its guards until the self-migration task
- [x] #5 `plugins/ralph/skills/ralph-init/SKILL.md` covers both Init and Upgrade for the change, and `README.md` describes the marker, the switches, the shims and the one-time migration
- [x] #6 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From the TASK-295 review: ralph-init SKILL.md's plugin-installed preflight (Step 1, the find over $CLAUDE_DIR/plugins/cache) still checks the cache by glob and does not check jq, while ralph.sh/refine.sh now resolve through installed_plugins.json with jq. Switch that check to the registry resolver (templates/shims/resolve-plugin.sh) when ralph-init moves to plugin-delivered files.

Plan: delete templates/claude/hooks/, templates/git-hooks/ and templates/claude/settings.json (legacy guard wiring Init no longer writes); trim templates/claude/settings.local.json to the project-only Skill(...) rules (the common rules come from user-settings.json). Retarget managed-file-drift.sh and migrate-plugin-hooks.sh legacy-copy comparisons to the plugin's hooks/ and git-hooks/ (byte-identical today). Init: Step 1 preflight via the registry resolver (resolve-plugin.sh), user settings via merge-user-settings.sh, last act = migrate-plugin-hooks.sh tracked + clone. Upgrade: tracked (asking about --local-guards for customised guards) + clone instead of overwriting guards/hooks/settings; second host runs only clone after git pull. Tests: parity now compares this repo's live .claude/hooks and .git/hooks with plugins/ralph/hooks and git-hooks; settings.json moves to the repo-local legacy list until TASK-302. README: marker, switches, shims, one-time migration.

Commit: `d146b2d` - task-301: switch ralph-init Init and Upgrade to the plugin-delivered guards, git hooks and allow rules

Implemented: template guard copies, git hook bodies and the legacy settings.json template deleted; settings.local.json template holds only the Skill(...) rules. Init: Step 1 uses the registry resolver (resolve-plugin.sh, closes the TASK-295 note), Step 3.7a offers merge-user-settings.sh, Step 3.11 runs tracked then clone as the last act. Upgrade: U2 reports the plugin-hooks state and compares legacy copies with plugins/ralph/hooks and git-hooks; U4 runs tracked (asking about --local-guards) and clone, merges template rules into settings.local.json instead of overwriting; a second host runs only clone after git pull. managed-file-drift.sh and migrate-plugin-hooks.sh compare legacy copies with the plugin's own files; the settings.json drift row is gone. Parity (template-parity.bats, R11 table) compares this repo's live guards and git hooks with the plugin; the live settings.json stays legacy wiring until TASK-302. Legacy fixtures for tests: tests/python/fixtures/legacy-claude-settings.json and legacy-settings.local.json. New tests/python/test_ralph_init_plugin_delivered.py runs Step 3.11 as written on a fresh repo. Checks: ruff clean, pytest 1238 passed / 4 skipped, bats tests/unit 207/207.

Commit: `db2842d` - task-301: point the sandbox notes at the user-settings fragment and rewrap two comments

Commit: `02f2ffa` - task-301: rewrap the managed-guards comment in migrate-plugin-hooks.sh

Review: ralph:task-reviewer APPROVED (score 9) after one round; it fixed the stale sandbox notes in SKILL.md (now pointing at the user-settings fragment), then rewrapped the long comments. Final checks: ruff clean, pytest 1238 passed / 4 skipped, bats tests/unit 207/207.

Commit: `e59e9df` - task-301: bump plugin version to 0.18.2 (patch)
<!-- SECTION:NOTES:END -->
