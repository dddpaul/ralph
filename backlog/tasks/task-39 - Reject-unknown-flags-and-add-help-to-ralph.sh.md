---
id: TASK-39
title: Reject unknown flags and add --help to ralph.sh
status: Done
assignee: []
created_date: '2026-04-20 16:15'
updated_date: '2026-04-20 18:28'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The catch-all case in arg parsing (line 91) silently swallows unknown flags like --typo. Change it to: error on unknown --* flags with a message, only accept bare numbers as positional max_iterations. Also add --help and --version flags. --help prints usage and exits 0. --version prints a version string and exits 0.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Unknown --flags produce an error message and exit 1
- [ ] #2 Bare numbers still accepted as max_iterations
- [ ] #3 --help prints usage text and exits 0
- [ ] #4 --version prints version and exits 0
- [ ] #5 All existing tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented --help (show_help function), --version (RALPH_VERSION=0.5.0), unknown --flag rejection with error+exit 1, non-numeric positional arg rejection. Added RALPH_SOURCE_ONLY guard around arg parsing to keep unit tests working. Files changed: ralph.sh. 129/130 tests pass (1 pre-existing failure unrelated).
<!-- SECTION:NOTES:END -->
