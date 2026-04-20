---
id: TASK-36
title: Remove duplicate format_duration function
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 16:15'
updated_date: '2026-04-20 17:02'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lines 210-222 (_summary_format_duration) and 383-396 (format_duration) are identical. Remove one and alias or call the other. Keep format_duration as the canonical name since it has no underscore prefix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Only one duration formatting function exists in ralph.sh
- [x] #2 Both print_summary and main loop use the same function
- [x] #3 All existing tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Move format_duration to line 210 (replacing _summary_format_duration), remove duplicate at line 383, update callers in print_summary.

Commit: `b6901df` - task-36: Deduplicate format_duration in ralph.sh

Removed duplicate _summary_format_duration, kept format_duration as canonical. Updated 3 test cases. Net -16 lines.
<!-- SECTION:NOTES:END -->
