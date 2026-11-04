---
id: TASK-295
title: Resolve the installed ralph plugin through the Claude Code plugin registry
status: Done
assignee: []
created_date: '2026-11-04T14:51:00Z'
updated_date: '2026-11-04T16:44:00Z'
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
- [x] #9 (host) Scope precedence is verified against real Claude Code with a project-scope install in an isolated test clone and the result is recorded in the notes
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

macOS host check for AC #9, part 1 (Claude Code 2.1.309, isolated CLAUDE_CONFIG_DIR, test clone). A user-scope install (1.0.0) followed by a project-scope install (2.0.0) from one marketplace makes Claude Code write two registry entries under plugins["ralph@dddpaul-ralph"] in a version 2 registry: scope user with projectPath null, and scope project with projectPath equal to the clone root as pwd -P prints it, each with its own versioned installPath. ralph_resolve_plugin picks the project entry (2.0.0) from the clone root, a subdirectory and a linked worktree, and the user entry (1.0.0) from an unrelated repo. claude plugin list shows both entries as enabled from any directory, so it does not reveal which one a session loads. With a local directory marketplace (marketplace add ./path), Claude Code loads plugin components from the marketplace source folder, not from the registry installPath. The real dddpaul-ralph marketplace is git-sourced, and git-sourced plugins load from their cache installPath (the agent-chat plugin's hooks.json path in a debug log). Part 2, observing which installPath a session loads when both scopes exist for a git-sourced marketplace, waits for the 0.16.0 push: 0.14.15 is already installed at user scope in a second isolated config.

macOS host check for AC #9, part 2 (Claude Code 2.1.309, isolated CLAUDE_CONFIG_DIR, git-sourced marketplace dddpaul/ralph). Version 0.14.15 was installed at user scope before the 0.16.0 push, then 0.16.0 at project scope in a test clone after it. The registry lists the user entry first and the project entry second. Which install a session loads was read from the debug log line 'Attempting to load skills from plugin ralph default skillsPath'. In that natural order, sessions in the clone root, in a clone subdirectory and in an unrelated repo all load the user-scope 0.14.15. After reversing the two array entries (timestamps unchanged), a session in the clone loads the project-scope 0.16.0, and one in the unrelated repo still loads 0.14.15. Claude Code therefore uses the first applicable entry in registry order, not project-before-user. The resolver as merged (project entry wins) picks 0.16.0 in the clone in the natural order, so the git shims and Claude hooks would run different versions. Verification done and recorded; the AC #3 rule must change to first-applicable-entry-in-registry-order. That change is filed as a follow-up task, not made here.
<!-- SECTION:NOTES:END -->
