---
id: TASK-33
title: Add --prompt-file flag to ralph.sh
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 13:52'
updated_date: '2026-04-20 15:18'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently the prompt sent to the AI tool is hardcoded in ralph.sh (lines 492-502). Add a --prompt-file <path> flag that loads the prompt template from a file. The MODE_PREFIX is still prepended automatically. If --prompt-file is not specified, use the existing hardcoded prompt as fallback. The prompt is identical for both claude and opencode tools — load once and use in both branches.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph.sh accepts --prompt-file <path> and --prompt-file=<path> arguments
- [x] #2 Invalid path (non-existent or unreadable file) produces clear error and exits with code 1
- [x] #3 When --prompt-file is provided, file content is used as prompt body with MODE_PREFIX prepended
- [x] #4 When --prompt-file is omitted, existing hardcoded prompt is used unchanged
- [x] #5 Unit tests verify argument parsing for --prompt-file
- [x] #6 Integration tests verify prompt loading from file and fallback behavior
- [x] #7 All existing tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Add PROMPT_FILE variable and --prompt-file/--prompt-file= parsing in the argument loop. 2) Add validation after existing validators: check file exists and is readable if --prompt-file provided. 3) In the retry loop (around line 492), load prompt body from file or fall back to hardcoded text, prepend MODE_PREFIX. 4) Update usage comment. 5) Add unit tests for arg parsing in argument-validation.bats. 6) Add integration tests for prompt loading and fallback in prompt-generation.bats.

Commit: `526360a` - task-33: Add --prompt-file flag to ralph.sh

Implemented --prompt-file flag. Added arg parsing (--prompt-file and --prompt-file=), validation for file readability, prompt loading from file with MODE_PREFIX prepended, and fallback to hardcoded default. Refactored prompt construction to load once and use in both claude/opencode branches. Files: ralph.sh, tests/unit/argument-validation.bats, tests/integration/prompt-generation.bats.
<!-- SECTION:NOTES:END -->
