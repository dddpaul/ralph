---
id: TASK-37
title: Fix EXEC_PREFIX word-splitting for paths with spaces
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 16:15'
updated_date: '2026-04-20 17:33'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Line 499 builds EXEC_PREFIX as a string and line 519 expands it unquoted. If SCRIPT_DIR contains spaces, devcontainer exec --workspace-folder breaks. Replace with an array: EXEC_PREFIX=() and EXEC_PREFIX=(devcontainer exec --workspace-folder "$SCRIPT_DIR"), then use ${EXEC_PREFIX[@]:+"${EXEC_PREFIX[@]}"} in the command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 EXEC_PREFIX is an array, not a string
- [x] #2 devcontainer exec works when SCRIPT_DIR contains spaces
- [x] #3 Non-devcontainer mode still works (empty array)
- [x] #4 All existing tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Convert EXEC_PREFIX from string to bash array. Empty array for non-devcontainer, populated array for devcontainer. Use ${EXEC_PREFIX[@]:+"${EXEC_PREFIX[@]}"} pattern for safe expansion at the two usage sites (lines 512, 515).

Commit: `182b28c` - task-37: Use array for EXEC_PREFIX to handle paths with spaces

Converted EXEC_PREFIX from string to bash array. Uses ${EXEC_PREFIX[@]:+"${EXEC_PREFIX[@]}"} expansion pattern at both usage sites (opencode and claude commands). Pre-existing test 123 failure confirmed on master.
<!-- SECTION:NOTES:END -->
