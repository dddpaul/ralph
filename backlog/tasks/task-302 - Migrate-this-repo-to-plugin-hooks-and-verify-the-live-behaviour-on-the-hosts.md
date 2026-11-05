---
id: TASK-302
title: Migrate this repo to plugin hooks and verify the live behaviour on the hosts
status: To Do
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-05T05:25:00Z'
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
- [ ] #2 (host) In a migrated test project the plugin commit-message guard blocks a bad git commit, including from a subdirectory session, and the same command is not blocked in a non-Ralph project
- [ ] #3 (host) A Ralph run in the devcontainer of a migrated test project is blocked by the plugin guard, including on a first run with no plugin data dir
- [ ] #4 (host) In a migrated test clone a plain git commit runs the plugin pre-commit, which rejects a non-NFC filename and a name over 125 bytes
- [ ] #5 (host) The plugin git hooks still run with the plugin disabled in Claude
- [ ] #6 (host) With an isolated CLAUDE_CONFIG_DIR whose registry points at a removed install, the commit fails with the repair message and --no-verify gets through
- [ ] #7 (host) On the second host, after the plugin update and the clone step, a commit runs the plugin hooks
- [ ] #8 (host) The tracked and clone steps for this repo run interactively on the macOS host, never from the devcontainer, and this repo own pre-push stays a plain hook until TASK-311 ships the plugin pre-push body
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Blocked in autonomous mode (Ralph iteration, devcontainer, 2026-11-04); nothing was migrated. Three reasons:
1. AC#2 would block every push in this repo. The plugin ships no git-hooks/pre-push until TASK-311, which is still To Do. With the shim installed as pre-push and ralph.pluginHooks true, the shim runs pre-push.local (version-bump-guard), then fails to resolve git-hooks/pre-push ('not found in the installed plugin') and exits 1 per FR-5. So every git push would need --no-verify, and that also skips version-bump-guard. Either run US-008 after TASK-311, or add TASK-311 as a dependency, or install only the clone-step shims now and convert pre-push later.
2. The clone step has to run on the host, not in the devcontainer. This container shares the host's .git/config. Here clone would record ralph.projectPath=/workspace (the host identity is the host path that the registry records) and ralph.jq=/usr/bin/jq. Those values would then be wrong for host-side commits.
3. AC#3 to AC#8 are host checks: an installed plugin, isolated test projects and configs, a devcontainer run, and the second host. A Ralph iteration cannot do them.
Facts checked: all six live guards in .claude/hooks are managed (so --local-guards lists all six and tracked only writes the marker and the .gitignore exception). .git/hooks pre-commit and commit-msg are byte-identical to plugins/ralph/git-hooks. post-commit differs and is listed in .claude/managed-file-drift.accept with the current hashes, so clone keeps it as post-commit.local. The installed plugin 0.18.2 (user scope) has git-hooks/{pre-commit,commit-msg,post-commit} and no pre-push.
Recommendation: run this interactively on the host after the pre-push question is settled.

Re-checked 2026-11-04 (Ralph iteration 8, devcontainer): still blocked for the same reasons. TASK-311 is still To Do, so the plugin has no git-hooks/pre-push. The session still runs in the devcontainer, so the clone step and the host checks (AC#3-#8) cannot run here. Nothing was migrated. A human has to run this on the host, after TASK-311 or with a decision on pre-push.

Reworked on 2026-11-05 after an autonomous run spent seven iterations rediscovering the same blockers. (1) Moved the old AC #2, this repo's pre-push becoming pre-push.local behind the shim, to TASK-311. Until the plugin ships git-hooks/pre-push, the shim cannot resolve a pre-push body and fails closed, which would block every push or force --no-verify, and --no-verify also skips version-bump-guard. (2) This task runs interactively on the host. The devcontainer shares the host's .git/config, so running the clone step there would record container values (ralph.projectPath=/workspace and the container's jq path) as this clone's settings. AC #3 to AC #8 already need the host.
<!-- SECTION:NOTES:END -->
