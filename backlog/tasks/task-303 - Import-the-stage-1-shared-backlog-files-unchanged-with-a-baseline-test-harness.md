---
id: TASK-303
title: Import the stage-1 shared-backlog files unchanged with a baseline test harness
status: Done
assignee: []
created_date: '2026-11-04T14:53:00Z'
updated_date: '2026-11-05T05:30:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Import a sibling project's proven stage-1 shared-backlog files unchanged, with a harness that runs their original test suite. This is the baseline every later protocol change diffs against.

The source is a sibling project at commit af5b1f8:
- scripts/shared-backlog.sh;
- scripts/hooks/pre-push;
- scripts/tests/shared-backlog-test.sh, with 75 tests.

The test expects its original folder layout, so the harness rebuilds that layout in a temp directory.

Run this task INTERACTIVELY on the host, not in Ralph: the devcontainer cannot see the source repo.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-009.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The stage-1 script, pre-push hook and test script are copied byte-identical from af5b1f8 to plugins/ralph/scripts/shared-backlog.sh, tests/shell/stage1/pre-push and tests/shell/stage1/shared-backlog-test.sh, with sha256 sums in the notes
- [x] #2 An unchanged reference copy is kept as tests/shell/stage1/shared-backlog.sh.orig and the baseline never tests the hardened script
- [x] #3 A pytest harness rebuilds the stage-1 layout (scripts/shared-backlog.sh, scripts/hooks/pre-push, scripts/tests/) in a temp directory and runs the unchanged test there
- [x] #4 (host) All 75 baseline tests pass under /bin/bash 3.2
- [x] #5 The task is run interactively on the host, not by Ralph, because the devcontainer cannot see the source repo
- [x] #6 ruff, pytest and bats pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: copy the three stage-1 files byte-identical from the sibling project at af5b1f8: the script to plugins/ralph/scripts/shared-backlog.sh (the copy later tasks harden) and to tests/shell/stage1/shared-backlog.sh.orig (the unchanged reference); the pre-push hook to tests/shell/stage1/pre-push; the test script to tests/shell/stage1/shared-backlog-test.sh. Add tests/python/test_shared_backlog_stage1.py: it pins the three reference files by sha256 and runs the unchanged suite in a temp directory rebuilt in the stage-1 layout (scripts/, scripts/hooks/, scripts/tests/, backlog/config.yml), never against the hardened plugin copy. Run interactively on the host because the devcontainer cannot see the source repo. The owner decided (2026-11-04) to keep the files byte-identical, including the script's comment that names the source project.

Imported byte-identical from af5b1f8 (sha256): plugins/ralph/scripts/shared-backlog.sh and tests/shell/stage1/shared-backlog.sh.orig both 0da8293dff6254cf13bd6bbf806f5ed86a6f835d1ec597adbf1e614b55b75b0a (source scripts/shared-backlog.sh); tests/shell/stage1/pre-push db0cc145ef6102b6bf745102bb527b2c66b9dbfe9c34f59e8053b7ae5f9a994b (source scripts/hooks/pre-push); tests/shell/stage1/shared-backlog-test.sh b94ed435e5e30a4794405cc1210ddfa36a924b0581a5075ecdd016b7e5b0f498 (source scripts/tests/shared-backlog-test.sh). All four are mode 100755. The harness pins the three reference files by these sums. macOS host check for AC #4: in the rebuilt stage-1 layout, /bin/bash 3.2.57 ran the unchanged suite with a PATH shim so that bash inside the suite also resolved to /bin/bash 3.2: passed 75, failed 0. Under Homebrew bash 5.3.20: passed 75, failed 0. Host gates on task-303: ruff clean; uv run pytest 1264 passed / 5 skipped, including the 4 new harness tests; LC_ALL=C bats tests/unit with no failures.

Commit: `275c2db` - task-303: import the stage-1 shared-backlog script with a pinned baseline suite

Commit: `3a6ad75` - task-303: isolate the stage-1 baseline from host env and the live backlog config

task-reviewer: APPROVED (0 blocking, 2 minor, SCORE 8). Both minor findings were fixed before merge. (1) The harness ran the suite with the full host environment, and the reviewer showed an exported SHARED_BACKLOG_CHECKS=true failing 2 of 75 cases. The suite now runs without SHARED_BACKLOG_* and without GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE, and with SHARED_BACKLOG_CHECKS=true exported the harness passes 4/4. (2) The harness copied this repo's live backlog/config.yml. It now uses a pinned fixture, tests/shell/stage1/config.yml, so a later config change cannot break the baseline. After the fixes: ruff clean; uv run pytest 1264 passed / 5 skipped; LC_ALL=C bats tests/unit with no failures.

Commit: `a88cdcb` - task-303: bump plugin version to 0.18.4 (patch)
<!-- SECTION:NOTES:END -->
