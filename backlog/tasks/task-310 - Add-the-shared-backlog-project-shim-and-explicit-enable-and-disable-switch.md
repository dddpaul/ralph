---
id: TASK-310
title: Add the shared-backlog project shim and explicit enable and disable switch
status: Done
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-06T15:13:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-295
  - TASK-300
  - TASK-304
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the tracked project shim for the shared-backlog script, and the explicit enable and disable switch.

enable:
- requires the marker's sharedBacklog true;
- sets the trusted git config ralph.sharedBacklog;
- installs the pre-push shim;
- saves the host's default holder.

disable clears the switch, and the clone migration never turns it back on.

The release gate (FR-13) keeps enable refusing until US-026.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-016 and FR-2, FR-13.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 templates/shims/shared-backlog.sh is a tracked fixed shim that embeds the TASK-295 resolver and execs the plugin shared-backlog script
- [x] #2 The script carries a release gate that stays closed until the release task, and enable refuses with shared-backlog protocol not released yet while it is closed
- [x] #3 Tests open the gate only through SHARED_BACKLOG_ALLOW_UNRELEASED=1
- [x] #4 enable requires the marker sharedBacklog true, sets git config ralph.sharedBacklog true, installs the pre-push shim and saves the host default holder in ralph.holder after asking once
- [x] #5 disable clears ralph.sharedBacklog, and rerunning the clone migration afterwards does not turn it back on (tested)
- [x] #6 A commit that removes the marker does not change the clone switch (tested)
- [x] #7 ralph-init Init and Upgrade offer the opt-in, write sharedBacklog and an optional checks into the marker, and run enable in that clone
- [x] #8 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: release gate (RELEASED=0, SHARED_BACKLOG_ALLOW_UNRELEASED=1 opens it) plus enable/disable in plugins/ralph/scripts/shared-backlog.sh; enable checks marker, holder and pre-push before writing, installs templates/shims/git-hook as pre-push (existing hook kept as pre-push.local), sets ralph.sharedBacklog last. New fixed shim templates/shims/shared-backlog.sh embeds the resolver. ralph-init Init Q5 + Step 3.11 sh snippet, Upgrade U4 opt-in bullet. Tests in tests/python/test_shared_backlog_enable.py.

Commit: `5a69b49` - task-310: add shared-backlog project shim, release gate and enable/disable switch

Commit: `a67c1db` - task-310: single-quote the checks command in the Init opt-in snippet

Done. enable/disable live in plugins/ralph/scripts/shared-backlog.sh behind RELEASED=0 (TASK-320 opens it). enable keeps an existing pre-push as pre-push.local and refuses before writing when a differing pre-push.local exists; disable unsets ralph.sharedBacklog and leaves the pre-push shim and ralph.holder. Until TASK-311 ships git-hooks/pre-push, an enabled clone's pre-push shim would block pushes; the closed gate prevents that. Init snippet uses an sh fence because test_ralph_init_plugin_delivered requires exactly one bash fence in Step 3.11. task-reviewer: APPROVED (minor checks-quoting note fixed). Full pytest 1331 passed; bats all ok.
<!-- SECTION:NOTES:END -->
