---
id: TASK-330
title: Retire the leftover filename-length-guard.sh legacy copy
status: Done
assignee: []
created_date: '2026-11-07T17:16:00Z'
updated_date: '2026-11-07T17:37:00Z'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Both clones have migrated to plugin hook shims (TASK-300/302) and have run migrate-plugin-hooks.sh clone, so .claude/hooks/filename-length-guard.sh is now a leftover legacy copy: the plugin-delivered pre-commit shim covers the filename length check on its own. migrate-plugin-hooks.sh tracked --retire-legacy already implements the retirement (deletes the file and its wiring, refuses if any clone's pre-commit is not yet the plugin shim). This task runs that subcommand and updates every test that still names the retired file.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Running 'bash <installed ralph plugin>/skills/ralph-init/scripts/migrate-plugin-hooks.sh tracked --retire-legacy' deletes .claude/hooks/filename-length-guard.sh and any .claude/settings.json wiring that named it, and the change is committed on the task branch
- [x] #2 tests/unit/filename-length-guard.bats, pre-commit-hook.bats, pretools-hooks.bats and template-parity.bats no longer assert on the retired file's presence or content
- [x] #3 tests/python/test_managed_file_drift.py, test_git_hook_shim.py, test_plugin_hooks.py, test_migrate_plugin_hooks.py, test_preflight_plugin_hooks.py and test_shorten_backlog_filenames.py no longer reference filename-length-guard.sh as a tracked/managed file
- [x] #4 A repo-wide grep for filename-length-guard.sh after the change finds no references to this repo's retired .claude/hooks copy as a live or tracked file (the shipped plugins/ralph/hooks guard, the plugin fallback for other projects' legacy copies, and changelog/task-history text remain)
- [x] #5 bash -n on migrate-plugin-hooks.sh passes and ruff, pytest and bats all pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `f329b91` - task-330: retire the legacy .claude/hooks/filename-length-guard.sh copy

Plan: run installed plugin (0.22.2) migrate-plugin-hooks.sh tracked --retire-legacy; repoint tests that read this repo's .claude/hooks copy to plugins/ralph/hooks; keep tests that build temp legacy projects (they cover the plugin's fallback for unmigrated projects).
AC#4 interpretation: plugins/ralph/hooks/filename-length-guard.sh is the shipped guard and stays, as do plugin references to it and the pre-commit/drift/preflight fallback for other projects' legacy copies. The grep target is references to this repo's retired .claude/hooks copy.

Review: APPROVED f329b91e307d5e3d9eadf3b4d9b495013db8ca10
Follow-up: .claude/task-reviewer-rules.md R11 still says the seven Ralph guards have .claude/hooks copies; this repo now keeps six.

Done: retired .claude/hooks/filename-length-guard.sh via installed plugin migrate-plugin-hooks.sh tracked --retire-legacy; tests repointed to the plugin guard; ruff, pytest (1486 passed), bats unit/integration/e2e all pass.
<!-- SECTION:NOTES:END -->
