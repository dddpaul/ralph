---
id: TASK-37
title: Fix EXEC_PREFIX word-splitting for paths with spaces
status: To Do
assignee: []
created_date: '2026-04-20 16:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Line 499 builds EXEC_PREFIX as a string and line 519 expands it unquoted. If SCRIPT_DIR contains spaces, devcontainer exec --workspace-folder breaks. Replace with an array: EXEC_PREFIX=() and EXEC_PREFIX=(devcontainer exec --workspace-folder "$SCRIPT_DIR"), then use ${EXEC_PREFIX[@]:+"${EXEC_PREFIX[@]}"} in the command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 EXEC_PREFIX is an array, not a string
- [ ] #2 devcontainer exec works when SCRIPT_DIR contains spaces
- [ ] #3 Non-devcontainer mode still works (empty array)
- [ ] #4 All existing tests pass
<!-- AC:END -->
