---
id: TASK-39
title: Reject unknown flags and add --help to ralph.sh
status: To Do
assignee: []
created_date: '2026-04-20 16:15'
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
