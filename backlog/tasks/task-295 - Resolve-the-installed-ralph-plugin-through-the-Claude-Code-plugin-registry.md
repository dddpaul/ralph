---
id: TASK-295
title: Resolve the installed ralph plugin through the Claude Code plugin registry
status: To Do
assignee: []
created_date: '2026-11-04T14:51:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Shims and ralph.sh must run the plugin version Claude Code actually installed.

Today ralph.sh picks the newest folder under the plugin cache by sort -V over whole paths. That ranks the marketplace name above the version, so a fork called ralph or a leftover newer folder wins.

The replacement is one resolver block that reads the plugin registry. Every shim, ralph.sh and refine.sh embed it.

Contracts:
- Registry: (config)/plugins/installed_plugins.json, version 2, key ralph@dddpaul-ralph. Each entry has scope, version, installPath and projectPath.
- Project identity, used to match a project-scope entry:
  - git config ralph.projectPath, which the clone migration saves as the host's canonical main worktree root;
  - otherwise the canonical parent of git rev-parse --git-common-dir.
- Inside the devcontainer the clone is mounted at /workspace, so the saved identity is what makes a host project-scope install match there.
- jq: PATH first, then git config ralph.jq.
- Config dir: CLAUDE_CONFIG_DIR, then git config ralph.claudeConfigDir, then HOME/.claude.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-001 and FR-3. Criteria marked (host) are checked on the macOS host and recorded in the notes before the task counts as complete.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 One resolver block lives in plugins/ralph/skills/ralph-init/templates/shims/resolve-plugin.sh, and a test fails when any shim template, ralph.sh or refine.sh embeds a different copy
- [ ] #2 The resolver reads installed_plugins.json with jq, requires registry version 2 and selects ralph@dddpaul-ralph
- [ ] #3 A project-scope entry whose projectPath equals the project identity (git config ralph.projectPath, else the canonical parent of the git common dir) wins over the user-scope entry
- [ ] #4 A separate-git-dir layout is rejected with an explicit message
- [ ] #5 Two candidate entries, a missing installPath, a missing target file, a wrong registry version and missing jq each fail with a distinct message
- [ ] #6 jq comes from PATH, else git config ralph.jq; the config dir comes from CLAUDE_CONFIG_DIR, else git config ralph.claudeConfigDir, else HOME/.claude
- [ ] #7 Tests resolve a project-only install with no user fallback from the host path, a /workspace mount and a linked worktree, and cover paths with spaces and a zz-fork cache entry
- [ ] #8 ralph.sh and refine.sh resolve the orchestrator through the resolver and no sort -V over cache paths remains
- [ ] #9 (host) Scope precedence is verified against real Claude Code with a project-scope install in an isolated test clone and the result is recorded in the notes
- [ ] #10 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
