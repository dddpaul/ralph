---
id: TASK-45
title: Sync ralph-init template ralph.sh with current ralph.sh
status: To Do
assignee: []
created_date: '2026-04-20 20:12'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
skills/ralph-init/templates/ralph.sh is severely outdated (~307 lines vs ~635 lines). Missing: status file tracking, run summary, --prompt-file/--help/--version flags, set -u, double-run guard, _update_status, cleanup traps, interrupt handlers, RALPH_SOURCE_ONLY guard. Template uses set -eo pipefail vs set -uo pipefail. Template only allows integer timeouts. Copy current ralph.sh as the new template.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Template ralph.sh matches current ralph.sh in features and structure
- [ ] #2 Template has same flags as current ralph.sh
- [ ] #3 Template uses set -uo pipefail
- [ ] #4 Template supports fractional timeouts
<!-- AC:END -->
