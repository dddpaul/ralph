---
id: TASK-311
title: Refuse pushes that carry duplicate task IDs with a plugin pre-push body
status: Done
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-07T11:55:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-297
  - TASK-305
  - TASK-307
  - TASK-308
  - TASK-310
  - TASK-322
  - TASK-302
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the plugin's pre-push body, which refuses a push carrying a duplicate task ID. A duplicate arrives with no git conflict, because the file names differ.

It acts on the trusted switch ralph.sharedBacklog, runs the read-only check-dupes on every pushed SHA without taking a lock, and chains (name).local.

It includes the end-to-end test: a real create push through the shim while create holds the lock, completing without deadlock.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-017.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/git-hooks/pre-push acts when ralph.sharedBacklog is true, buffers stdin, runs the read-only check-dupes on every pushed SHA without taking a lock, and skips ref deletions
- [x] #2 Tests show it refuses a tip carrying a duplicate, including one in a draft, and refuses when backlog is missing
- [x] #3 Tests show it passes a ref deletion and a push of several refs
- [x] #4 It keeps enforcing after a commit that removes the marker while the clone switch is on
- [x] #5 An existing hook keeps running as pre-push.local with the same stdin
- [x] #6 An end-to-end test runs a real create push through the installed shim while create holds the protocol lock, and it completes without deadlock
- [x] #7 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
- [x] #8 This repo own pre-push (the version-bump guard) works as pre-push.local behind the plugin pre-push shim: a real push of a bumped commit to a scratch remote still runs the version-bump guard (moved here from TASK-302). The live move in this clone is TASK-328, because it needs the installed plugin to carry git-hooks/pre-push first
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From the TASK-302 review (2026-11-05): moving this repo's pre-push behind the plugin pre-push shim (AC #8) needs either a managed-file-drift.accept entry for .git/hooks/pre-push, so that clone keeps it as pre-push.local, or a manual move. clone stops on a differing hook the accept file does not list. Added TASK-302 as a dependency, because the move assumes this repo is already migrated.

Plan: add plugins/ralph/git-hooks/pre-push (acts on git config ralph.sharedBacklog only, buffers stdin, runs the plugin's read-only check-dupes on each non-deleted pushed SHA, no lock). Test it with tests/shell/shared-backlog-prepush-test.sh plus a pytest harness: real pushes through the shim that enable installs, with the registry pointed at this repo's plugins/ralph. Cover duplicate task and draft IDs, a missing backlog, deletions, several refs, marker removal, pre-push.local stdin, a real create under the protocol lock, and the version-bump guard as pre-push.local in a scratch repo.
AC #8 split: moving this clone's live .git/hooks/pre-push now would block every push. The installed plugin is 0.20.2 and has no git-hooks/pre-push, and ralph.pluginHooks is true, so the shim fails closed. --no-verify would also skip version-bump-guard. The scratch-remote proof stays here. The live move is TASK-328 (host, after the plugin update). AC #8 text was reworded to match.

AC #7 (host) deferred: the container's /bin/bash is 5.2, so test_bash32_syntax skips its 3.2 run. On a Mac host run: /bin/bash tests/shell/shared-backlog-prepush-test.sh (must end with failed: 0). bash -n, the static bash-4 builtin guard, the new suite and all other shell suites pass under bash 5.2.

Commit: `9887fd7` - task-311: add the plugin pre-push body that refuses pushes carrying duplicate task IDs

Commit: `821de4c` - task-311: keep check-dupes off the hook's ref list and scope the legacy-copy note

Review: task-reviewer APPROVED (score 8, 0 blocking). Both minor findings are fixed: check-dupes now reads </dev/null, so a future stdin reader cannot swallow ref lines, and the README legacy-copy sentence is limited to the three shimmed hooks. Final checks: ruff clean, pytest 1348 passed / 4 skipped, bats 0 failures, pre-push suite 44/44. The live move of this clone's pre-push is TASK-328 (host, after the plugin update).

Commit: `95b2a16` - task-311: bump plugin version to 0.21.3 (patch)

Commit: `ca909a2` - task-311: trace the pre-push body through a PATH bash wrapper so the bash 3.2 run covers it

AC #7 host part, macOS host (2026-11-07): with a /bin/bash 3.2.57 symlink first on PATH, /bin/bash tests/shell/shared-backlog-prepush-test.sh gives passed: 44, failed: 0, and the trace shows the plugin pre-push body and check-dupes running under 3.2; the same suite gives 44/44 with the default bash 5.3. The earlier BASH_ENV trace could not see the body under bash 3.2 (task-reviewer B1), fixed in ca909a2 by tracing through a PATH bash wrapper; README now names TASK-328 as the gate for moving this repo's pre-push.
Review: APPROVED ca909a21ce97a25812109cc4ad6c46e0decb9f29
Follow-up: tests/shell/shared-backlog-prepush-test.sh:136 has "duplicate task IDs in", which also matches the success line "no duplicate task IDs in 1 pushed ref(s)"; the refusal is still proven by the section's other checks (task-reviewer minor, 9887fd7).

Commit: `8a4591c` - task-311: bump plugin version to 0.22.2, past origin's 0.22.1

Integration review: APPROVED e81cbbc6a78165481a3f28f64031613184740eff
<!-- SECTION:NOTES:END -->
