---
id: TASK-64
title: Fix mktemp sandbox compatibility in preflight.sh
status: Done
assignee:
  - '@claude'
created_date: '2026-04-25 17:28'
updated_date: '2026-04-25 17:29'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
preflight.sh uses bare mktemp which writes to system temp dir. Claude Code sandbox blocks this, causing false 'syntax error' failures. Use TMPDIR-aware mktemp instead.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 preflight.sh uses TMPDIR for temp file creation
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Use TMPDIR-aware mktemp in preflight.sh syntax check.

Changed mktemp to use TMPDIR with /tmp fallback. All 8 tests pass.

Commit: `21f57b4` - task-64: Use TMPDIR-aware mktemp in preflight.sh
<!-- SECTION:NOTES:END -->
