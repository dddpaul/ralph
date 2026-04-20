---
id: TASK-33
title: Add --prompt-file flag to ralph.sh
status: To Do
assignee: []
created_date: '2026-04-20 13:52'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently the prompt sent to the AI tool is hardcoded in ralph.sh (lines 492-502). Add a --prompt-file <path> flag that loads the prompt template from a file. The MODE_PREFIX is still prepended automatically. If --prompt-file is not specified, use the existing hardcoded prompt as fallback. The prompt is identical for both claude and opencode tools — load once and use in both branches.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh accepts --prompt-file <path> and --prompt-file=<path> arguments
- [ ] #2 Invalid path (non-existent or unreadable file) produces clear error and exits with code 1
- [ ] #3 When --prompt-file is provided, file content is used as prompt body with MODE_PREFIX prepended
- [ ] #4 When --prompt-file is omitted, existing hardcoded prompt is used unchanged
- [ ] #5 Unit tests verify argument parsing for --prompt-file
- [ ] #6 Integration tests verify prompt loading from file and fallback behavior
- [ ] #7 All existing tests pass
<!-- AC:END -->
