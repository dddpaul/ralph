---
id: TASK-320
title: Release the shared-backlog protocol once every part is done
status: To Do
assignee: []
created_date: '2026-11-04T14:55:00Z'
updated_date: '2026-11-07T16:10:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-308
  - TASK-311
  - TASK-313
  - TASK-315
  - TASK-316
  - TASK-317
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Open the shared-backlog release gate once every part of the protocol is Done, so that no intermediate commit exposed half of it.

It adds the user docs, and an end-to-end (host) check on two clones of one test origin.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-026 and FR-13.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The release gate in plugins/ralph/scripts/shared-backlog.sh is opened, after TASK-308, TASK-311, TASK-313, TASK-315, TASK-316 and TASK-317 are Done
- [ ] #2 enable works without SHARED_BACKLOG_ALLOW_UNRELEASED and no production path sets that variable (checked by grep)
- [ ] #3 `README.md` and the ralph-init docs describe the protocol: opt-in, enable, disable and the commands
- [ ] #4 (host) On two clones of one test origin, enable plus two racing creates, two racing default-mode Ralph claims and one integrate produce no duplicate ID and no double claim
- [ ] #5 ruff, pytest and bats pass
- [ ] #6 On the macOS host /bin/bash tests/shell/shared-backlog-retry-test.sh ends with failed: 0: its sneak_hook strips the padding BSD wc -l adds (n=$(wc -l <file | tr -d ' ')), so the subject is exactly "unrelated 0"
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Pointer: TASK-328 AC #3 is still open (live part). The push that lands this task bumps the plugin version through this Mac's pre-push shim (pre-push.local runs the version-bump guard first). Record that push's command, rc and origin range in TASK-328, then check its AC #3 and set it Done.
<!-- SECTION:NOTES:END -->
