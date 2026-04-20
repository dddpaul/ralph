---
id: TASK-36
title: Remove duplicate format_duration function
status: To Do
assignee: []
created_date: '2026-04-20 16:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lines 210-222 (_summary_format_duration) and 383-396 (format_duration) are identical. Remove one and alias or call the other. Keep format_duration as the canonical name since it has no underscore prefix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Only one duration formatting function exists in ralph.sh
- [ ] #2 Both print_summary and main loop use the same function
- [ ] #3 All existing tests pass
<!-- AC:END -->
