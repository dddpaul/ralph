---
id: TASK-321
title: Match the plugin resolver to Claude Code first-applicable registry entry
status: To Do
assignee: []
created_date: '2026-11-04T16:56:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-295
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: TASK-295's host check on Claude Code 2.1.309 found how Claude Code picks among the entries of plugins["ralph@dddpaul-ralph"] in installed_plugins.json. It loads the first entry, in registry array order, that applies to the current project:
- a user-scope entry applies everywhere;
- a project-scope entry applies only where its projectPath matches.

New installs are appended. In the usual order, user installed first and project later, Claude therefore runs the user install even inside the project.

The resolver merged in TASK-295 always prefers the project entry. In that common case the git shims and the Claude hooks would run different plugin versions.

Fix: change the selection in the resolver block (`plugins/ralph/skills/ralph-init/templates/shims/resolve-plugin.sh`) to the first entry in array order that applies. An entry applies when:
- its scope is user; or
- its scope is project or local, and its projectPath equals the project identity (git config ralph.projectPath, else the canonical main worktree root).

The existing errors stay: missing registry, wrong registry version, no jq, missing installPath, missing target file. The two-candidate ambiguity error goes, because Claude Code itself takes the first applicable entry.

Every embedded copy is updated through the parity test: ralph.sh, refine.sh and the shim templates.

This ordering is undocumented Claude Code behaviour. The tests pin it, and the PRD records the Claude Code version it was observed on.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-001 and FR-3. Criteria marked (host) are checked on the macOS host and recorded in the notes before the task counts as complete.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The resolver selects the first entry of plugins["ralph@dddpaul-ralph"] in registry order whose scope is user, or whose scope is project or local with projectPath equal to the project identity
- [ ] #2 Fake-registry tests: user-then-project resolves the user entry in the clone; project-then-user resolves the project entry in the clone and the user entry in an unrelated repo; a local-scope entry behaves like a project-scope one; no applicable entry fails with a distinct message
- [ ] #3 The two-candidate ambiguity error is removed and its test replaced
- [ ] #4 Every embedded copy of the block (ralph.sh, refine.sh, shim templates) matches the updated block and the parity test passes
- [ ] #5 PRD US-001 and FR-3 in design/plugin-delivered-project-files-prd.md describe the first-applicable-entry rule and name Claude Code 2.1.309 as the version observed
- [ ] #6 (host) In an isolated CLAUDE_CONFIG_DIR holding a user and a project install of different versions from the git-sourced marketplace, the resolver and a Claude Code session pick the same installPath in both registry orders, recorded in the notes
- [ ] #7 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
