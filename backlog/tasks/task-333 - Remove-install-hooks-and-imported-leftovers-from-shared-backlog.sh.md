---
id: TASK-333
title: Remove install-hooks and imported leftovers from shared-backlog.sh
status: To Do
assignee: []
created_date: '2026-11-07T21:35:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: the feature review of plugin-delivered-project-files (design/plugin-delivered-project-files-review-2026-11-07.md) found leftovers from the stage-1 import in the shipped plugins/ralph/scripts/shared-backlog.sh. The repo is public and every Ralph project runs this script.

1. install-hooks. The locked design dropped it, but the script still ships it: header lines 33-34, HOOK_MARKER at line 92 (used only by it), cmd_install_hooks at lines 1059-1074 and the dispatch entry at line 1184. README.md line 226 lists it in the shared-backlog command table. It copies scripts/hooks/pre-push, a file no Ralph project has, so it fails in practice; with --force it replaces the plugin pre-push shim with a hook that is not the shim. enable already installs the pre-push shim, so remove install-hooks entirely.

2. Header lines 5-7 send the reader to a 'Shared repo protocol' section of CLAUDE.md and to a multi-host-parallel-work design document of the project the script came from. Neither exists in Ralph projects. Point to the README section 'Shared backlog across hosts' instead.

3. Six messages name the repo owner. Use these words instead:
   - line 747: claim refused; only a person may decide to override it with --force
   - line 788: TASK-$TASK_ID is held by $who, not $HOLDER; only a person may decide to override it with --force
   - line 1041: ...rerun integrate; else stop and ask a person
   - lines 1046, 1052, 1054: keep each message and end it with: stop and ask a person

4. tests/shell/shared-backlog-prepush-test.sh line 136 checks for 'duplicate task IDs in', which also matches the success line 'no duplicate task IDs in 1 pushed ref(s)'. Anchor it on the refusal text (TASK-311 follow-up).

Do not touch tests/shell/stage1/: it is the pinned import baseline, and test_shared_backlog_stage1.py checks its sha256 values.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 shared-backlog.sh has no install-hooks: no header lines, no cmd_install_hooks, no HOOK_MARKER and no dispatch entry; shared-backlog.sh install-hooks ends in the usage error like any unknown command (test)
- [ ] #2 grep -rn install-hooks README.md plugins/ prints nothing
- [ ] #3 The script header points to the README section 'Shared backlog across hosts'; grep -n -E 'Shared repo protocol|multi-host-parallel-work' plugins/ralph/scripts/shared-backlog.sh prints nothing
- [ ] #4 No message names a person: grep -n -E 'say-so|stop and tell' plugins/ralph/scripts/shared-backlog.sh prints nothing, and the six messages read as given in the description
- [ ] #5 The prepush suite's refusal check no longer matches the success line, and the suite still passes
- [ ] #6 git diff --stat master..HEAD shows no path under tests/shell/stage1/
- [ ] #7 bash -n, the bash 3.2 static guard, the shared-backlog shell suites, ruff and pytest pass
<!-- AC:END -->
