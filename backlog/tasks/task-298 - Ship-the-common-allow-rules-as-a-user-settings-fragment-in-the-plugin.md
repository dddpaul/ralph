---
id: TASK-298
title: Ship the common allow rules as a user-settings fragment in the plugin
status: Done
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-04T16:36:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ship the common allow rules as one plugin fragment that lands in user settings, so that projects carry only their extras.

A plugin cannot ship allow rules itself:
- On the second host, configuration management merges the fragment.
- On the Mac, the preflight lists what is missing, and the owner adds it.

The 7 Skill(...) rules are dropped, because a test in -p mode showed skills need no allow rule. Interactive mode is still to be confirmed on the host.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-004.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/user-settings.json holds the 46 Bash rules and ScheduleWakeup from the template settings.local.json, attribution with empty commit and pr, and sandbox with enabled and autoAllowBashIfSandboxed
- [x] #2 The fragment holds no Skill(...) rules
- [x] #3 The /ralph-run preflight prints one warning listing exactly the fragment entries missing from the user settings and changes no file
- [x] #4 A merge helper appends missing allow entries to a sample user settings file, keeps every unrelated key and value, and reports a differing scalar without overwriting it
- [x] #5 (host) In an interactive session in a project without Skill(...) rules, /ralph-status runs with no permission prompt, and the result is recorded in the notes
- [x] #6 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: generate plugins/ralph/user-settings.json from the template settings.local.json minus the 7 Skill(...) rules; add ralph.user_settings (missing_entries + non-overwriting merge, CLI behind merge-user-settings.sh); add a report-only preflight check 9 that prints one stderr warning listing the missing entries; tests in tests/python/test_user_settings_fragment.py; docs in ralph-run SKILL.md and README.

Commit: `9ed8338` - task-298: ship the common allow rules as a user-settings fragment with a preflight check and a merge helper

AC #5 deferred (host): it needs an interactive Claude Code session on the Mac host, which this container cannot run (the -p mode test already showed skills need no allow rule). Follow-up on the host: in a test project whose .claude/settings.local.json has no Skill(...) rules, start an interactive session, run /ralph-status, confirm no permission prompt appears, then check AC #5 and append the result (Claude Code version, prompt yes/no) to these notes. If a prompt appears, the Skill(...) rules go back into plugins/ralph/user-settings.json.

Commit: `68d7747` - task-298: count the user-settings fragment as a shipped plugin file

Done: plugins/ralph/user-settings.json (46 Bash rules + ScheduleWakeup, attribution, sandbox; no Skill rules); ralph.user_settings (missing_entries, non-overwriting merge) with merge-user-settings.sh shim; preflight check 9 prints one stderr warning listing missing entries and writes nothing; the preflight fixture pins CLAUDE_CONFIG_DIR to a dir seeded with the fragment; the fragment joins the shipped set. ruff clean, pytest 1112 passed, bats 265/266 (the one failure, R11 settings.local.json shape, is a known local gitignored-file failure that also happens on master). task-reviewer APPROVED after two fixes (AC #5 deferral note, shipped-set entry).

Commit: `a0094a8` - task-298: bump plugin version to 0.16.0 (minor)

macOS host check for AC #5 (2026-11-04). In an interactive Claude Code session in a project with no Skill(...) allow rules (user settings hold none either), typing /ralph:ralph-status ran the skill with no permission prompt: it read the status file path and reported that Ralph had not run there. A user-typed slash command does not exercise the model's Skill tool permission path; that path was covered on 2026-11-04 by claude -p in default permission mode, where the model invoked a plugin skill through the Skill tool with no allow rule, then with a short-name rule, then with a plugin:skill rule, and the permission check passed in 2-5 ms each time. The fragment's omission of Skill(...) rules stands.
<!-- SECTION:NOTES:END -->
