---
id: TASK-320
title: Release the shared-backlog protocol once every part is done
status: To Do
assignee: []
created_date: '2026-11-04T14:55:00Z'
updated_date: '2026-11-07T16:25:00Z'
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
- [ ] #7 pyproject.toml pins ruff to one exact version (ruff==0.17.3, the version the box and the devcontainer resolve and under which the current tree passes) so uv run ruff check . gives the same result on every host; uv.lock stays gitignored; the 5 E402 findings the macOS host's ruff 0.15.18 reports are gone after uv sync
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Pointer: TASK-328 AC #3 is still open (live part). The push that lands this task bumps the plugin version through this Mac's pre-push shim (pre-push.local runs the version-bump guard first). Record that push's command, rc and origin range in TASK-328, then check its AC #3 and set it Done.

Ruff (2026-11-07): uv.lock is gitignored and pyproject.toml has only ruff>=0.7.0, so each host resolves its own ruff. The macOS host's venv has 0.15.18 and reports 5 E402 (ralph_orchestrator.py:25-27, refine_orchestrator.py:26, tests/fixtures/fake_refine_claude.py:43), because TASK-312 and TASK-315 dropped the '# noqa: E402' comments as unused under ruff 0.17.3. TASK-312's notes already logged 'pin ruff in pyproject' as a follow-up; AC #7 does that. Check AC #5 under the pinned version.
<!-- SECTION:NOTES:END -->
