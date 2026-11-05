---
id: TASK-302
title: Migrate this repo to plugin hooks and verify the live behaviour on the hosts
status: Done
assignee: []
created_date: '2026-11-04T14:52:00Z'
updated_date: '2026-11-05T07:17:00Z'
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
- [x] #1 This repo is migrated with tracked --local-guards listing every live guard, plus clone, and its live guard copies and their registrations remain
- [x] #2 (host) In a migrated test project the plugin commit-message guard blocks a bad git commit, including from a subdirectory session, and the same command is not blocked in a non-Ralph project
- [x] #3 (host) A Ralph run in the devcontainer of a migrated test project is blocked by the plugin guard, including on a first run with no plugin data dir
- [x] #4 (host) In a migrated test clone a plain git commit runs the plugin pre-commit, which rejects an NFD path that duplicates an NFC tree path and a name over 125 bytes
- [x] #5 (host) The plugin git hooks still run with the plugin disabled in Claude
- [x] #6 (host) With an isolated CLAUDE_CONFIG_DIR whose registry points at a removed install, the commit fails with the repair message and --no-verify gets through
- [ ] #7 (host) On the second host, after the plugin update and the clone step, a commit runs the plugin hooks
- [x] #8 (host) The tracked and clone steps for this repo run interactively on the macOS host, never from the devcontainer, and this repo own pre-push stays a plain hook until TASK-311 ships the plugin pre-push body
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

Plan (interactive, macOS host, 2026-11-05): (1) run the installed plugin's migrate-plugin-hooks.sh tracked --local-guards with all six managed guards (commit-msg-guard, commit-prefix-guard, master-branch-guard, naming-guard, notes-guard, task-validator), so this repo keeps its live copies and their settings.json registrations for testing its own changes; (2) run clone on the host. pre-commit and commit-msg already equal the plugin bodies and are replaced by the shim. post-commit is accepted in managed-file-drift.accept and becomes post-commit.local. pre-push, this repo's version-bump hook, is not touched and stays a plain hook until TASK-311. (3) Check commits and the guards in this repo. (4) Run AC #2 to #6 in isolated test projects and configs; AC #7, the second host, needs Paul on the box.

Commit: `cfecee5` - task-302: migrate this repo to the plugin hooks with its live guards kept local

Host evidence, 2026-11-05 (macOS, installed plugin 0.18.2, Claude Code 2.1.309).

Migration of this repo (AC #1, AC #8):
- The installed plugin's migrate-plugin-hooks.sh ran on the host, never in the devcontainer.
- tracked --local-guards commit-msg-guard,commit-prefix-guard,master-branch-guard,naming-guard,notes-guard,task-validator wrote .claude/ralph.json (pluginHooks true, all six in localGuards) and added !.claude/ralph.json to .gitignore. All 13 settings.json entries and every live guard copy remain.
- clone installed the shim as pre-commit, commit-msg and post-commit. It set ralph.pluginHooks true, ralph.jq=/opt/homebrew/bin/jq and ralph.projectPath=/Users/paul/Private/Projects/ai/ralph (host values). It kept the accepted post-commit as post-commit.local.
- It also kept all 44 fragment allow rules in .claude/settings.local.json, because the user settings lack them.
- pre-push, this repo's version-bump hook, is untouched and stays a plain hook until TASK-311.
- The migration commit cfecee5 went through the shims, and the plugin post-commit recorded it once.

AC #2 (claude -p sessions with the real user config, the session mode Ralph uses):
- The command was a plain git commit carrying an AI attribution trailer.
- In a migrated test project, and in a session started in its sub/dir, the debug log shows the plugin's run.sh commit-msg-guard returned permissionDecision deny, and no commit landed.
- In a plain repo with no marker, run.sh ran, exited 0, and the commit landed.

AC #3:
- Inside this repo's devcontainer, claude -p --dangerously-skip-permissions in a nested migrated test repo was denied by the same plugin guard, and no commit landed.
- The ralph plugin data dir was absent right before that run (checked inside the container) and was recreated by it.

AC #4, in a migrated test clone with no .claude/hooks:
- The plugin pre-commit, through the shim, rejected an over-long name with exit 1 (the 125-byte filename cap).
- It rejected a staged NFD path duplicating an existing NFC tree path with exit 1.
- The hook rejects NFC/NFD duplicates, not every NFD name. The AC wording 'a non-NFC filename' is looser than the hook.

AC #5:
- With an isolated CLAUDE_CONFIG_DIR holding the real registry and the ralph plugin disabled in enabledPlugins, the over-long name was still rejected with exit 1.

AC #6:
- With an isolated CLAUDE_CONFIG_DIR whose registry installPath points at /nonexistent, the commit failed with exit 1. The message named the missing installPath, said the hook cannot be resolved while ralph.pluginHooks is true, and named installing or updating the plugin and the --no-verify bypass.
- The --no-verify commit then exited 0.

Also done in this task:
- (a) post-commit.local was the plugin post-commit body plus the TASK-217 bump nudge, so the commit-notes part would have run twice. It is reduced by hand to the nudge only.
- (b) The CLAUDE.md line in .claude/managed-file-drift.accept is refreshed against the repo templates (0.18.4); the drift check is clean.
- (c) tests/unit/template-parity.bats is aware of the migration state. In a migrated clone (ralph.pluginHooks true), .git/hooks/* must equal templates/shims/git-hook and post-commit.local may carry only the nudge. Otherwise the legacy checks apply, verified by forcing ralph.pluginHooks false through GIT_CONFIG_* (the legacy checks then fail against the shims, as expected).

Findings for follow-up tasks, to file after the agentbox run is integrated so task IDs cannot collide:
- F1: git options before the subcommand (git -c key=value commit ...) do not match the if: Bash(git commit *) filter, so the Claude commit guards never run, in legacy and plugin wiring alike. The git commit-msg hook still blocks trailers, but the branch-prefix rule exists only as a Claude guard.
- F2: clone turns an accepted hook that is a modified copy of the plugin body into a .local that duplicates the plugin's work. It should refuse or report it, so it gets reduced to the project-only delta. This belongs with TASK-323.

AC #7 (second host) is deferred. On agentbox, after the pull and the plugin update to 0.18.4:
1. run migrate-plugin-hooks.sh clone;
2. replace .git/hooks/post-commit.local with the nudge-only version (the same file as the Mac's);
3. check that a commit runs the plugin hooks.

Commit: `6748bf1` - task-302: check git hook parity against the shim in a migrated clone and refresh the CLAUDE.md accept line

AC #3 verification note, for review: AC #3 can only be checked on the host with a Claude session inside the devcontainer, which a reviewer cannot re-run. The recorded run is in this session's transcript (tool_use toolu_01Ud5PJdoYHVnMAhbHCT6whh). Its output was 'data dir before: absent', the plugin guard's BLOCKED message, 'commits: 1' (no new commit), and the debug line where run.sh commit-msg-guard returned permissionDecision deny.

To re-run it on the host, in a nested test repo under the workspace that has ralph.sh and .claude/ralph.json with pluginHooks true:
1. rmdir ~/.claude/plugins/data/ralph-dddpaul-ralph
2. devcontainer exec --workspace-folder . bash -c 'cd /workspace/<probe> && claude --dangerously-skip-permissions --print < prompt.txt'
3. Use a prompt asking the session to run a plain git commit that carries an AI attribution trailer.

Review fixes after CHANGES REQUESTED (round 1):
- In a migrated clone, the post-commit parity test now compares .git/hooks/post-commit with the shim instead of skipping it. In a scratch clone, a non-shim post-commit now fails the test and the shim passes.
- The exact-pair failure message names the template actually compared.
- The stale comment about this repo's legacy wiring is updated.
- !.claude/ralph.json moved into the .claude exceptions block of .gitignore.

Commit: `901ced4` - task-302: check post-commit against the shim in a migrated clone and tidy the parity test

AC #4 reworded on 2026-11-05 with the owner's agreement, here and in PRD US-008, to match the hook's design (TASK-136): the plugin pre-commit rejects an NFD path that duplicates an NFC tree path. A lone NFD name is accepted, which the reviewer reproduced. It creates no duplicate, and git on macOS precomposes names by default. The tested behaviour, an NFD duplicate rejected with exit 1, is unchanged.

Commit: `4a66b65` - task-302: word the NFC criterion as rejecting NFD duplicates of tree paths

Review round 2 returned CHANGES REQUESTED: 1 blocking, 2 minor. Fixes:
- Blocking: PRD US-008 still said this repo's pre-push becomes pre-push.local behind the shim. That contradicted the owner-approved rework that moved the criterion to TASK-311. US-008 now says the pre-push stays a plain hook until US-017, and the move is an explicit criterion of US-017, the story TASK-311 implements.
- Minor: README.md no longer says this repo keeps its legacy wiring until TASK-302. It describes the migrated state (localGuards, shims, pre-push until TASK-311).
- Minor: the nudge-line pattern is one shared NUDGE_LINES variable in tests/unit/template-parity.bats.

Also for a follow-up task, after the agentbox run is integrated (F3): .claude/task-reviewer-rules.md R11 still says settings.json is kept until the repo migrates (TASK-302). Its table should say that a migrated clone's .git/hooks/* are compared with the shim. Changing the rules file needs the owner's approval.

Gates after the fixes: ruff clean; uv run pytest 1264 passed / 5 skipped; LC_ALL=C bats tests/unit with no failures. With ralph.pluginHooks forced false, the legacy parity checks fail against the shims, as expected.

Commit: `876d8f9` - task-302: keep this repo's pre-push plain until US-017 and describe the migrated state

Commit: `f029db9` - task-302: name the post-commit parity test for both migration states

task-reviewer round 3: APPROVED (0 blocking, 1 minor, SCORE 9). The minor finding, a parity test named for the legacy state only, was fixed by renaming the test. Done with AC #7 (second host) deferred to agentbox, per the plan in these notes.
<!-- SECTION:NOTES:END -->
