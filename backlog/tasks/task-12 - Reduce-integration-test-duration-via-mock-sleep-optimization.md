---
id: TASK-12
title: Reduce integration test duration via mock sleep optimization
status: Done
assignee:
  - '@claude'
created_date: '2026-04-18 19:03'
updated_date: '2026-04-18 19:23'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reduce integration test suite duration (~135s) by optimizing mock sleep values. No production code changes — only test mocks. Three changes: (1) reduce sleep 30 to sleep 3 in run-summary-integration.bats signal test mock, (2) reduce sleep 3 to sleep 1.5 in mock_opencode_with_timeout across timeout-handling.bats, (3) adjust any outer timeout wrappers accordingly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Signal test (summary on signal shows interrupted) completes in under 10s
- [x] #2 Timeout tests (tests 32-34, 37, 41) each complete in under 5s
- [x] #3 All integration tests still pass
- [x] #4 No production code changes (ralph.sh, lib/ unchanged)
- [ ] #5 Total integration suite completes in under 80s
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Change sleep 30 → sleep 3 in run-summary-integration.bats line 105, (2) Change mock_opencode_with_timeout calls from 3 → 1.5 at lines 77/87/98/162/209 in timeout-handling.bats, (3) Reduce outer timeout 30 → 10 wrappers accordingly. No production code changes.

AC #5: Suite runs ~92s vs original ~135s (32% improvement). The 80s target is not achievable without production code changes — ralph.sh truncates TIMEOUT_SEC to integer via %d format, creating a 1s floor per timeout iteration. 42 tests × ~2s startup overhead = ~84s baseline. Changes made: sleep 30→3 (signal test), sleep 3→1 (timeout mocks), sleep 0.5→0.1 (normal mock), timeout 30→10/15 (outer wrappers).

Commit: `bc759eb` - task-12: Reduce mock sleep values in integration tests

Implemented: reduced sleep 30→3 (signal test), sleep 3→1 (timeout mocks), sleep 0.5→0.1 (normal mock), timeout 30→10/15 (outer wrappers). Files: tests/integration/run-summary-integration.bats, tests/integration/timeout-handling.bats. Suite time ~135s→~92s (32% improvement). AC #5 (under 80s) not achievable without production code changes due to TIMEOUT_SEC integer floor.
<!-- SECTION:NOTES:END -->
