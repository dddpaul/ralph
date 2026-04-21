---
id: TASK-56
title: Add integration test for --on-error continue behavior
status: To Do
assignee: []
created_date: '2026-04-21 18:33'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
No test validates that --on-error continue skips failed iterations without exiting. Add tests verifying: (1) ralph continues to next iteration after tool failure, (2) failed iteration is not counted as completed, (3) summary shows correct failed_iterations count.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Test verifies ralph continues after tool failure with --on-error continue
- [ ] #2 Test verifies TASKS_COMPLETED does not include failed iterations
- [ ] #3 Test verifies FAILED_ITERATIONS count in summary
<!-- AC:END -->
