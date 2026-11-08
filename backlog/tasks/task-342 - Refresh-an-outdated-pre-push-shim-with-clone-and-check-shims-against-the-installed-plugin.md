---
id: TASK-342
title: >-
  Refresh an outdated pre-push shim with clone and check shims against the
  installed plugin
status: To Do
assignee: []
created_date: '2026-11-08T15:03:00Z'
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
- [ ] #1 migrate-plugin-hooks.sh clone replaces a pre-push equal to a recorded past shim (the git-hook-shim.v0.25.10 fixture) with the current template, leaves pre-push.local unchanged, and a second run changes nothing (pytest)
- [ ] #2 clone leaves pre-push untouched when it is missing, is already the current shim, or is any other file, and never creates it (pytest)
- [ ] #3 preflight reports 'shims outdated in this clone' naming pre-push when pre-push is a recorded past shim, and adds no warning for a missing pre-push or one that is not a recorded shim (pytest)
- [ ] #4 preflight compares the hooks with the shim and hash list of the install the registry resolves for the project, and falls back to its own plugin root when resolution fails: with a fake registry whose install ships a newer shim, a hook equal to preflight's own copy is reported as outdated (pytest)
- [ ] #5 README.md and .claude/RELEASING.md say that clone also refreshes an outdated pre-push shim
- [ ] #6 bash -n and the bash 3.2 static guard pass on the changed scripts; ruff, pytest and bats pass
<!-- AC:END -->
