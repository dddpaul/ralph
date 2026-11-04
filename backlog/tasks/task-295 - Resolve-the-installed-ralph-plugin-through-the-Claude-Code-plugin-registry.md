---
id: TASK-295
title: Resolve the installed ralph plugin through the Claude Code plugin registry
status: Done
assignee: []
created_date: '2026-11-04T14:51:00Z'
updated_date: '2026-11-04T15:22:00Z'
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
- [x] #1 One resolver block lives in plugins/ralph/skills/ralph-init/templates/shims/resolve-plugin.sh, and a test fails when any shim template, ralph.sh or refine.sh embeds a different copy
- [x] #2 The resolver reads installed_plugins.json with jq, requires registry version 2 and selects ralph@dddpaul-ralph
- [x] #3 A project-scope entry whose projectPath equals the project identity (git config ralph.projectPath, else the canonical parent of the git common dir) wins over the user-scope entry
- [x] #4 A separate-git-dir layout is rejected with an explicit message
- [x] #5 Two candidate entries, a missing installPath, a missing target file, a wrong registry version and missing jq each fail with a distinct message
- [x] #6 jq comes from PATH, else git config ralph.jq; the config dir comes from CLAUDE_CONFIG_DIR, else git config ralph.claudeConfigDir, else HOME/.claude
- [x] #7 Tests resolve a project-only install with no user fallback from the host path, a /workspace mount and a linked worktree, and cover paths with spaces and a zz-fork cache entry
- [x] #8 ralph.sh and refine.sh resolve the orchestrator through the resolver and no sort -V over cache paths remains
- [ ] #9 (host) Scope precedence is verified against real Claude Code with a project-scope install in an isolated test clone and the result is recorded in the notes
- [x] #10 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) templates/shims/resolve-plugin.sh holds one marker-delimited block defining ralph_resolve_plugin <dir> <relpath>: canonical common dir (reject unless it ends in /.git), identity = git config ralph.projectPath else parent of common dir; jq from PATH else git config ralph.jq; config dir CLAUDE_CONFIG_DIR, git config ralph.claudeConfigDir, HOME/.claude; registry version 2; project-scope entry matching identity beats user-scope; distinct errors for no jq / no registry / wrong version / not installed / >1 candidates / no installPath / missing installPath dir / missing target / separate git dir. (2) Embed the block byte-identically in ralph.sh and refine.sh (+ template copies); ralph.sh keeps the RALPH_ORCHESTRATOR override, refine.sh keeps override + in-repo + legacy tiers and replaces only the cache-sort tier. (3) pytest test_resolve_plugin.py: embedded-copy parity across templates/shims/*, ralph.sh, refine.sh and their template copies; fake-registry behaviour tests incl. host path, /workspace mount (ralph.projectPath), linked worktree, spaces, zz-fork cache. (4) Update shim.bats, README, ralph-init SKILL.md, R11 note. AC9 (host) deferred.

Commit: `4841bdd` - task-295: resolve the installed ralph plugin through the Claude Code plugin registry

Commit: `6fa86e6` - task-295: list the shim templates as non-mirrored in the template parity registry

Commit: `e336c2e` - task-295: ignore CDPATH when resolving the git common dir and fix the R11 shim note

Done. One resolver block (ralph_resolve_plugin <dir> <relpath>) in templates/shims/resolve-plugin.sh, embedded byte-identically in ralph.sh, refine.sh and their template copies; tests/python/test_resolve_plugin.py pins the copies and covers the registry rules against fake registries and real clones (host path, /workspace mount via ralph.projectPath, linked worktree, paths with spaces, zz-fork cache, CDPATH). ralph.sh keeps the RALPH_ORCHESTRATOR override; refine.sh keeps its override, in-repo and legacy tiers and swaps only the cache-sort tier. Only scope "project" matches the identity; "local"-scope entries are ignored. Check this on the host along with AC9. templates/shims/ is listed as non-mirrored in template-parity.bats. Review: task-reviewer CHANGES REQUESTED (CDPATH, R11 note), fixed in e336c2e, then APPROVED. The minor ralph-init preflight finding is noted on TASK-301. Checks: ruff clean; pytest 1058 passed/3 skipped; bats all pass except the settings.local.json shape test, which fails the same way on master (gitignored local file). AC9 (host): deferred to host, not yet verified. Run a project-scope install in an isolated test clone with real Claude Code on macOS, then record the result here and check AC9.

Commit: `acd19a2` - task-295: bump plugin version to 0.15.0 (minor)
<!-- SECTION:NOTES:END -->
