---
id: TASK-41
title: Add set -u (nounset) to ralph.sh
status: To Do
assignee: []
created_date: '2026-04-20 16:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph.sh uses set -o pipefail but not set -u. Unset variable access fails silently. Add set -u and fix all unguarded variable references to use ${VAR:-} or ${VAR:-default} where needed. Audit every variable reference in the script.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 set -u is enabled alongside set -o pipefail
- [ ] #2 No unset variable errors when running normally
- [ ] #3 No unset variable errors when running with --on-error continue/retry
- [ ] #4 RALPH_SOURCE_ONLY guard still works
- [ ] #5 All existing tests pass
<!-- AC:END -->
