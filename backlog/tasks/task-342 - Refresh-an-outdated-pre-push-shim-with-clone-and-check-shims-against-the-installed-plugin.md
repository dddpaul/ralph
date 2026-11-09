---
id: TASK-342
title: >-
  Refresh an outdated pre-push shim with clone and check shims against the
  installed plugin
status: Done
assignee: []
created_date: '2026-11-08T15:03:00Z'
updated_date: '2026-11-09T05:54:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: the 2026-11-08 feature review (design/plugin-delivered-project-files-review-2026-11-08.md, notes 2 and 3) found that the documented refresh after a plugin release ('/plugin update', then 'migrate-plugin-hooks.sh clone' in each clone) misses pre-push, and that preflight can miss outdated shims.

1. clone manages only pre-commit, commit-msg and post-commit (SHIMMED in plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh). A pre-push that is an earlier shim stays old. shared-backlog.sh enable replaces a past pre-push shim (TASK-335), but only clones with ralph.sharedBacklog run enable, and no document says to rerun it. A clone that moved its pre-push by hand (this repo, TASK-328) has no tool at all: during TASK-341 both hosts copied the template over pre-push by hand. The v1 shim still works today because it execs git-hooks/pre-push itself, but later dispatcher changes will not reach that hook.
2. preflight's _SHIMMED_HOOKS (plugins/ralph/skills/ralph-run/scripts/ralph/preflight.py) leaves out pre-push, so an outdated pre-push shim is never reported.
3. preflight compares the hooks with the shim and hash list under its own plugin root (_PLUGIN_ROOT, derived from __file__), not with the install the registry names. A session that has not reloaded after /plugin update runs an older preflight, which can report no drift while the git hooks, which always resolve the registry, already run the new plugin. The review inferred this from a host note and did not reproduce it.

Fix:
- clone: when pre-push exists, its sha256 matches a 'shim <sha256>' line in shipped-git-hooks.sha256, and it differs from the current template, replace it in place the same way as the other hooks. Never create pre-push, never touch a pre-push that is not a recorded shim, and never touch pre-push.local. Installing pre-push stays the job of shared-backlog.sh enable.
- preflight: report a pre-push that is a recorded past shim under 'shims outdated in this clone', with the clone command. A missing pre-push, or one that is not a recorded shim, adds no warning, as today.
- preflight: take the shim template and the hash list from the install the registry names for this project, resolved the way the git hooks resolve it (the resolver in plugins/ralph/skills/ralph-init/templates/shims/resolve-plugin.sh, for example by sourcing it in a bash subprocess and asking for skills/ralph-init/templates/shims/git-hook). When resolution fails, fall back to its own plugin root as today. preflight stays read-only.
- README.md (the clone description and 'Releasing plugin updates') and .claude/RELEASING.md: say that clone also refreshes a pre-push that is an earlier shim.

The real v1 shim is in tests/python/fixtures/shipped-git-hooks/git-hook-shim.v0.25.10.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 migrate-plugin-hooks.sh clone replaces a pre-push equal to a recorded past shim (the git-hook-shim.v0.25.10 fixture) with the current template, leaves pre-push.local unchanged, and a second run changes nothing (pytest)
- [x] #2 clone leaves pre-push untouched when it is missing, is already the current shim, or is any other file, and never creates it (pytest)
- [x] #3 preflight reports 'shims outdated in this clone' naming pre-push when pre-push is a recorded past shim, and adds no warning for a missing pre-push or one that is not a recorded shim (pytest)
- [x] #4 preflight compares the hooks with the shim and hash list of the install the registry resolves for the project, and falls back to its own plugin root when resolution fails: with a fake registry whose install ships a newer shim, a hook equal to preflight's own copy is reported as outdated (pytest)
- [x] #5 README.md and .claude/RELEASING.md say that clone also refreshes an outdated pre-push shim
- [x] #6 bash -n and the bash 3.2 static guard pass on the changed scripts; ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: clone's plan_hooks adds pre-push:replace only when pre-push is a regular file, differs from the current shim and is a recorded 'shim' hash; preflight adds pre-push to the outdated check and takes shim/hash list/migrate script from the registry-resolved install (sourcing its own resolve-plugin.sh in bash), falling back to its own root; tests in test_migrate_plugin_hooks_clone.py and test_preflight_plugin_hooks.py; README + .claude/RELEASING.md.

Commit: `9972ab6` - task-342: refresh an earlier pre-push shim in clone and compare shims with the registry-resolved install in preflight

Commit: `68744a8` - task-342: restore the executable bit on migrate-plugin-hooks.sh and describe pre-push and the resolved install in the ralph-run preflight docs

Commit: `3c2dd4d` - task-342: list every preflight plugin-hooks state before the shim source sentence in ralph-run SKILL.md

Review: APPROVED 3c2dd4d4881b5782c1dbfd8d2b4877792f3b4abb

Done: clone refreshes a pre-push that is a recorded past shim (never creates it, never touches pre-push.local); preflight reports such a pre-push as outdated and takes shim, hash list and migrate script from the registry-resolved install (sourcing resolve-plugin.sh in bash), falling back to its own root. Docs: README, .claude/RELEASING.md, ralph-run SKILL.md. Final gate: ruff ok, pytest 1596 passed/4 skipped, bats 276 with 0 failures.

Commit: `c6c0f4d` - task-342: bump plugin version to 0.25.12 (patch)

Commit: `f97e38a` - task-342: bump plugin version to 0.25.13 (patch)

Version re-bump: TASK-343 on the other host also released 0.25.12, and origin's v0.25.12 tag points at its merge (beda54c). Following .claude/RELEASING.md 'Resolving a version conflict': deleted the unpushed local v0.25.12 tag, merged origin/master into master (b2716cd, Integrated-Origin trailer, tree equal to git merge-tree), and moved both manifests to 0.25.13 on task-342-version. bump-version.sh patch refused there because master..HEAD changes no shipped file, so the two version lines were set by hand to what the script writes. Checks on the merged tree on macOS: ruff clean; pytest 1598 passed in the sandbox, and the 3 sandbox-bound tests passed outside it; the seven bash 3.2 shared-backlog suites pass; bats passes except 3 usage-pause preflight tests that already fail on 3e125d7.

Review: APPROVED f97e38af39d4fad673dc98c89a64a582c6a6dbdc
<!-- SECTION:NOTES:END -->
