---
id: TASK-14
title: Isolate test status and log files from project directory
status: To Do
assignee: []
created_date: '2026-04-18 19:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Integration tests run ralph.sh from PROJECT_ROOT, overwriting backlog/.ralph-status.json and backlog/.ralph-run.log. Fix by making paths overridable via env vars. Changes: (1) ralph.sh lines 135-136: use RALPH_STATUS_FILE and RALPH_RUN_LOG env vars with current paths as defaults. (2) tests/helpers/common.bash setup_test_dir(): export RALPH_STATUS_FILE and RALPH_RUN_LOG pointing to TEST_DIR. (3) tests/integration/status-file-integration.bats: replace hardcoded PROJECT_ROOT/backlog paths at lines 5-6 with TEST_DIR paths, remove rm -f cleanup in setup/teardown since temp dir handles it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh uses RALPH_STATUS_FILE env var with fallback to SCRIPT_DIR/backlog/.ralph-status.json
- [ ] #2 ralph.sh uses RALPH_RUN_LOG env var with fallback to SCRIPT_DIR/backlog/.ralph-run.log
- [ ] #3 setup_test_dir in common.bash exports both env vars to TEST_DIR
- [ ] #4 status-file-integration.bats uses TEST_DIR paths instead of PROJECT_ROOT/backlog
- [ ] #5 All integration tests pass
- [ ] #6 Running tests does not modify backlog/.ralph-status.json or backlog/.ralph-run.log
<!-- AC:END -->
