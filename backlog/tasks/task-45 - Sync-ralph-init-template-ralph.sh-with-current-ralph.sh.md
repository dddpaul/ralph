---
id: TASK-45
title: Sync ralph-init template ralph.sh with current ralph.sh
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 20:12'
updated_date: '2026-04-20 20:20'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
skills/ralph-init/templates/ralph.sh is severely outdated (~307 lines vs ~635 lines). Missing: status file tracking, run summary, --prompt-file/--help/--version flags, set -u, double-run guard, _update_status, cleanup traps, interrupt handlers, RALPH_SOURCE_ONLY guard. Template uses set -eo pipefail vs set -uo pipefail. Template only allows integer timeouts. Copy current ralph.sh as the new template.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Template ralph.sh matches current ralph.sh in features and structure
- [x] #2 Template has same flags as current ralph.sh
- [x] #3 Template uses set -uo pipefail
- [x] #4 Template supports fractional timeouts
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Copy current ralph.sh as the new template at skills/ralph-init/templates/ralph.sh. The template is severely outdated (~307 lines vs ~635 lines) and missing many features. The current ralph.sh already has all required features (status tracking, run summary, all flags, set -uo pipefail, fractional timeouts, double-run guard, etc). Straight copy is the correct approach per the task description.

Commit: `e878682` - task-45: Sync ralph-init template ralph.sh with current ralph.sh

Copied current ralph.sh (635 lines) as the new template, replacing the outdated version (307 lines). Template now has all features: status file tracking, run summary, --prompt-file/--help/--version flags, set -uo pipefail, double-run guard, RALPH_SOURCE_ONLY guard, fractional timeouts, interrupt handlers, cleanup traps. Files changed: skills/ralph-init/templates/ralph.sh
<!-- SECTION:NOTES:END -->
