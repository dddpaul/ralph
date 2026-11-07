---
id: TASK-320
title: Release the shared-backlog protocol once every part is done
status: In Progress
assignee: []
created_date: '2026-11-04T14:55:00Z'
updated_date: '2026-11-07T16:54:00Z'
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
- [x] #1 The release gate in plugins/ralph/scripts/shared-backlog.sh is opened, after TASK-308, TASK-311, TASK-313, TASK-315, TASK-316 and TASK-317 are Done
- [x] #2 enable works without SHARED_BACKLOG_ALLOW_UNRELEASED and no production path sets that variable (checked by grep)
- [x] #3 `README.md` and the ralph-init docs describe the protocol: opt-in, enable, disable and the commands
- [ ] #4 (host) On two clones of one test origin, enable plus two racing creates, two racing default-mode Ralph claims and one integrate produce no duplicate ID and no double claim
- [x] #5 ruff, pytest and bats pass
- [ ] #6 On the macOS host /bin/bash tests/shell/shared-backlog-retry-test.sh ends with failed: 0: its sneak_hook strips the padding BSD wc -l adds (n=$(wc -l <file | tr -d ' ')), so the subject is exactly "unrelated 0"
- [x] #7 pyproject.toml pins ruff to one exact version (ruff==0.17.3, the version the box and the devcontainer resolve and under which the current tree passes) so uv run ruff check . gives the same result on every host; uv.lock stays gitignored; the 5 E402 findings the macOS host's ruff 0.15.18 reports are gone after uv sync
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Pointer: TASK-328 AC #3 is still open (live part). The push that lands this task bumps the plugin version through this Mac's pre-push shim (pre-push.local runs the version-bump guard first). Record that push's command, rc and origin range in TASK-328, then check its AC #3 and set it Done.

Ruff (2026-11-07): uv.lock is gitignored and pyproject.toml has only ruff>=0.7.0, so each host resolves its own ruff. The macOS host's venv has 0.15.18 and reports 5 E402 (ralph_orchestrator.py:25-27, refine_orchestrator.py:26, tests/fixtures/fake_refine_claude.py:43), because TASK-312 and TASK-315 dropped the '# noqa: E402' comments as unused under ruff 0.17.3. TASK-312's notes already logged 'pin ruff in pyproject' as a follow-up; AC #7 does that. Check AC #5 under the pinned version.

Plan: remove the release gate from plugins/ralph/scripts/shared-backlog.sh (RELEASED, release_gate and the SHARED_BACKLOG_ALLOW_UNRELEASED override) so enable always proceeds; drop the override from the tests and replace the closed-gate tests with enable-works-without-the-variable checks; drop the gate paragraph from ralph-init SKILL.md and push.py; document the protocol in README.md and ralph-init docs; pin ruff==0.17.3 in pyproject.toml; strip the BSD wc -l padding in sneak_hook. AC #4 and #6 are host checks this container cannot run.

Commit: `9f2f135` - task-320: release the shared-backlog protocol, document it and pin ruff

Deferred to the host (this Linux devcontainer cannot run them); record each result here, check the AC, then set Done:
- AC #4: on the Mac, make one bare test origin and two clones of it with .claude/ralph.json {"sharedBacklog": true, "checks": "true"}; run bash scripts/shared-backlog.sh enable --holder @host-a in one and --holder @host-b in the other; start two shared-backlog.sh create calls at once (one per clone), then two default-mode Ralph runs at once (one per clone) over one To Do task, then shared-backlog.sh integrate in one clone; after a sync, check-dupes on origin/master exits 0 and the To Do task carries exactly one holder.
- AC #6: on the Mac, /bin/bash tests/shell/shared-backlog-retry-test.sh ends with failed: 0 (the tr -d fix in sneak_hook is in the diff; the suite passes 38/0 here under GNU wc).

Commit: `dd3aa28` - task-320: list install-hooks in the README command table and keep the prepush test executable

Review: APPROVED dd3aa28e72c25a56ae14b264c586ee1c12dd3b53

Implemented (container part): release gate removed from shared-backlog.sh (RELEASED, release_gate, SHARED_BACKLOG_ALLOW_UNRELEASED gone; tests no longer set it); README 'Shared backlog across hosts' section and ralph-init SKILL.md commands paragraph; ruff==0.17.3 pinned (5 E402 gone after uv sync); sneak_hook strips BSD wc padding. ruff clean, pytest 1487 passed/4 skipped, bats 283/283, shared-backlog shell suites failed: 0. task-reviewer APPROVED (after fixing a lost exec bit on the prepush test and adding install-hooks to the README table). Status plan: like TASK-328, stays In Progress after merge until AC #4 and #6 run on the Mac host.

Commit: `61e452c` - task-320: bump plugin version to 0.25.1 (patch)
<!-- SECTION:NOTES:END -->
