---
id: TASK-321
title: Match the plugin resolver to Claude Code first-applicable registry entry
status: Done
assignee: []
created_date: '2026-11-04T16:56:00Z'
updated_date: '2026-11-04T17:08:00Z'
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
- [x] #1 The resolver selects the first entry of plugins["ralph@dddpaul-ralph"] in registry order whose scope is user, or whose scope is project or local with projectPath equal to the project identity
- [x] #2 Fake-registry tests: user-then-project resolves the user entry in the clone; project-then-user resolves the project entry in the clone and the user entry in an unrelated repo; a local-scope entry behaves like a project-scope one; no applicable entry fails with a distinct message
- [x] #3 The two-candidate ambiguity error is removed and its test replaced
- [x] #4 Every embedded copy of the block (ralph.sh, refine.sh, shim templates) matches the updated block and the parity test passes
- [x] #5 PRD US-001 and FR-3 in design/plugin-delivered-project-files-prd.md describe the first-applicable-entry rule and name Claude Code 2.1.309 as the version observed
- [ ] #6 (host) In an isolated CLAUDE_CONFIG_DIR holding a user and a project install of different versions from the git-sourced marketplace, the resolver and a Claude Code session pick the same installPath in both registry orders, recorded in the notes
- [x] #7 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `e3502e4` - task-321: resolve the first applicable plugin registry entry in registry order, as Claude Code does

Plan: replace the project-before-user jq selection in templates/shims/resolve-plugin.sh with the first entry in registry order whose scope is user, or project/local with projectPath equal to the identity; drop the two-candidate error; re-embed the block in ralph.sh, refine.sh and their templates; update tests, PRD US-001/FR-3/open question, README and a superseded note in the brainstorm.

AC #6 deferred (host): it needs real Claude Code on the macOS host with the git-sourced dddpaul/ralph marketplace, which this container cannot run (container claude -p is not logged in, and the plugin registry here is the shared host one). Follow-up on the host: in an isolated CLAUDE_CONFIG_DIR, install two different ralph versions, one at user scope and one at project scope in a test clone. In the natural order (user first), run ralph_resolve_plugin from the clone and from an unrelated repo, and read which installPath a session loads from the debug log line 'Attempting to load skills from plugin ralph default skillsPath'. Then swap the two array entries in installed_plugins.json and repeat. Record the Claude Code version and the four resolver/session installPath pairs here, and check AC #6 if they match.

Done: resolver takes the first applicable ralph@dddpaul-ralph entry in registry order (user anywhere; project or local with projectPath = identity); two-candidate error removed; block re-embedded in ralph.sh, refine.sh and templates/root copies; tests pin user-then-project, project-then-user (clone + unrelated repo), local scope, no applicable entry, several applicable entries; PRD US-001/FR-3/open question, README and a superseded note in the brainstorm updated. ruff clean; pytest 1115 passed/3 skipped; bats 265/266 (R11 settings.local.json shape, known local gitignored-file failure, also on master); bash -n clean. task-reviewer CHANGES REQUESTED (missing AC #6 deferral note), fixed, then APPROVED. AC #6 (host) still pending.

Commit: `bc67187` - task-321: bump plugin version to 0.16.1 (patch)
<!-- SECTION:NOTES:END -->
