---
id: TASK-19
title: Isolate test backlog directory from project backlog
status: To Do
assignee: []
created_date: '2026-04-19 10:19'
updated_date: '2026-04-19 10:42'
labels: []
dependencies:
  - TASK-14
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-14 isolates RALPH_STATUS_FILE and RALPH_RUN_LOG into TEST_DIR, but tests still operate on the real project's backlog/tasks/ via the backlog CLI. This means running tests while ralph is running (or in CI parallelism) can collide and corrupt task state.

Fix: add BACKLOG_DIR env var support to ralph.sh (and any helpers that call 'backlog'). When set, ralph.sh runs 'backlog' commands with cwd set to BACKLOG_DIR. In tests/helpers/common.bash, set BACKLOG_DIR="$TEST_DIR/backlog" and create a fresh backlog structure inside TEST_DIR for each test.

Depends on TASK-14 being merged first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh respects BACKLOG_DIR env var for all backlog CLI invocations
- [ ] #2 tests/helpers/common.bash sets BACKLOG_DIR to a per-test directory
- [ ] #3 Running integration tests in parallel (e.g. bats --jobs 4) does not corrupt project backlog/tasks/
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Decision: Closed without implementation (2026-04-19)

After brainstorming, determined this task is not needed.

**Findings:**
1. Tests already isolate via PATH manipulation (mock_backlog/mock_backlog_multi in tests/helpers/common.bash) — they never invoke the real backlog CLI
2. Backlog CLI has no --project-dir flag — implementation would require wrapping every backlog call in 'cd "$BACKLOG_DIR" && backlog ...', touching ~5 call sites in ralph.sh
3. No actual bug exists; this was preemptive defense against hypothetical scenarios:
   - Test author forgets mock_backlog → cheaper fix is a default failing stub in common.bash (5 lines, no ralph.sh changes)
   - Multi-tenant production Ralph instances → speculative; Ralph is designed as one-instance-per-checkout

**YAGNI applies.** Archiving.
<!-- SECTION:NOTES:END -->
