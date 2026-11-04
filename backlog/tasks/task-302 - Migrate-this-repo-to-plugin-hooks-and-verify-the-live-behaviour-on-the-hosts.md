---
id: TASK-302
title: Migrate this repo to plugin hooks and verify the live behaviour on the hosts
status: To Do
assignee: []
created_date: '2026-11-04T14:52:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-301
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrate this repo with its live guard copies kept as local overrides, and verify the live behaviour.

Most criteria are (host) checks with the installed plugin, in isolated test projects and test configs, never the real user config.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-008.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 This repo is migrated with tracked --local-guards listing every live guard, plus clone, and its live guard copies and their registrations remain
- [ ] #2 This repo own pre-push becomes pre-push.local behind the shim
- [ ] #3 (host) In a migrated test project the plugin commit-message guard blocks a bad git commit, including from a subdirectory session, and the same command is not blocked in a non-Ralph project
- [ ] #4 (host) A Ralph run in the devcontainer of a migrated test project is blocked by the plugin guard, including on a first run with no plugin data dir
- [ ] #5 (host) In a migrated test clone a plain git commit runs the plugin pre-commit, which rejects a non-NFC filename and a name over 125 bytes
- [ ] #6 (host) The plugin git hooks still run with the plugin disabled in Claude
- [ ] #7 (host) With an isolated CLAUDE_CONFIG_DIR whose registry points at a removed install, the commit fails with the repair message and --no-verify gets through
- [ ] #8 (host) On the second host, after the plugin update and the clone step, a commit runs the plugin hooks
<!-- AC:END -->
