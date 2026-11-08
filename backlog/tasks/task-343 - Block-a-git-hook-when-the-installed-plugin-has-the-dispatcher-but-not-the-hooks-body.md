---
id: TASK-343
title: >-
  Block a git hook when the installed plugin has the dispatcher but not the
  hook's body
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
Why: the 2026-11-08 feature review (design/plugin-delivered-project-files-review-2026-11-08.md, note 4) found that TASK-341 loosened FR-5. Before TASK-341 the shim resolved git-hooks/<name> itself, so an install without that body failed resolution and the shim blocked per switch: pre-commit and commit-msg when ralph.pluginHooks is true, pre-push when ralph.pluginHooks or ralph.sharedBacklog is true. Since TASK-341 the shim resolves only git-hooks/run. When run exists but git-hooks/<name> does not, run warns and exits 0 even with ralph.pluginHooks true; test_dispatcher_warns_and_exits_0_after_local_for_a_name_without_body pins this. All four bodies ship today, so nothing is exposed now, but a partial or broken install would let commits and pushes through with only a warning.

Fix in plugins/ralph/git-hooks/run, not in the shim, so no clone needs a refresh. When the body is missing, check the same switch table the shim uses before running <name>.local:

```bash
case "$name" in
  pre-commit | commit-msg) switches="ralph.pluginHooks" ;;
  pre-push) switches="ralph.pluginHooks ralph.sharedBacklog" ;;
  *) switches="" ;;
esac
```

If any listed switch is true (git config --bool), print a block line that names the hook, the missing body and the switch, then the shim's hint line ('ralph: install or update the ralph plugin, or bypass this once with --no-verify'), and exit 1 without running <name>.local. That matches the shim's own blocked path. Otherwise keep today's behaviour: run <name>.local (its failure stops the hook with its status), then warn that the body was skipped and exit 0. The table in run must stay identical to the one in plugins/ralph/skills/ralph-init/templates/shims/git-hook; add a test that compares them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With ralph.pluginHooks true and no pre-commit body beside run, the dispatcher exits 1, names the missing body and --no-verify on stderr, and does not run pre-commit.local (pytest)
- [ ] #2 pre-push with no body is blocked when ralph.pluginHooks is true and, separately, when only ralph.sharedBacklog is true (pytest)
- [ ] #3 With both switches off, and for post-commit or any name outside the table, the dispatcher runs <name>.local, then warns and exits 0 as before (pytest; adapt test_dispatcher_warns_and_exits_0_after_local_for_a_name_without_body)
- [ ] #4 A test fails when the switch table in git-hooks/run differs from the one in templates/shims/git-hook (pytest)
- [ ] #5 templates/shims/git-hook is unchanged (git diff master..HEAD --stat lists no change to it), and the README's dispatcher paragraph describes the block
- [ ] #6 bash -n and the bash 3.2 static guard pass on git-hooks/run; ruff, pytest and bats pass
<!-- AC:END -->
