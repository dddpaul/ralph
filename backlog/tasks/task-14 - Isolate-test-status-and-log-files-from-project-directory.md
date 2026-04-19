---
id: TASK-14
title: Isolate test status and log files from project directory
status: Done
assignee:
  - '@claude'
created_date: '2026-04-18 19:15'
updated_date: '2026-04-19 07:49'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Integration tests run ralph.sh from PROJECT_ROOT, overwriting backlog/.ralph-status.json and backlog/.ralph-run.log. Fix by making paths overridable via env vars. Changes: (1) ralph.sh lines 135-136: use RALPH_STATUS_FILE and RALPH_RUN_LOG env vars with current paths as defaults. (2) tests/helpers/common.bash setup_test_dir(): export RALPH_STATUS_FILE and RALPH_RUN_LOG pointing to TEST_DIR. (3) tests/integration/status-file-integration.bats: replace hardcoded PROJECT_ROOT/backlog paths at lines 5-6 with TEST_DIR paths, remove rm -f cleanup in setup/teardown since temp dir handles it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph.sh uses RALPH_STATUS_FILE env var with fallback to SCRIPT_DIR/backlog/.ralph-status.json
- [x] #2 ralph.sh uses RALPH_RUN_LOG env var with fallback to SCRIPT_DIR/backlog/.ralph-run.log
- [x] #3 setup_test_dir in common.bash exports both env vars to TEST_DIR
- [x] #4 status-file-integration.bats uses TEST_DIR paths instead of PROJECT_ROOT/backlog
- [x] #5 All integration tests pass
- [x] #6 Running tests does not modify backlog/.ralph-status.json or backlog/.ralph-run.log
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) ralph.sh lines 135-136: use RALPH_STATUS_FILE/RALPH_RUN_LOG env vars with current paths as defaults. (2) common.bash setup_test_dir: export both vars to TEST_DIR. (3) status-file-integration.bats: remove top-level STATUS_FILE/RUN_LOG, use TEST_DIR paths, remove rm -f cleanup.

Commit: `a9065d2` - task-14: Isolate test status and log files from project directory

Implemented env var overrides RALPH_STATUS_FILE and RALPH_RUN_LOG in ralph.sh with fallback defaults. Updated setup_test_dir to export both vars to TEST_DIR. Simplified status-file-integration.bats to use TEST_DIR paths. All 15 status-file integration tests pass. Tests no longer create files in project backlog directory.
<!-- SECTION:NOTES:END -->
