---
id: TASK-1
title: Fix PIPESTATUS bug in ralph.sh
status: To Do
assignee: []
created_date: '2026-04-16 07:52'
updated_date: '2026-04-17 07:49'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
EXIT_CODE=${PIPESTATUS[0]} after echo | timeout ... | tee may capture echo's exit code, not the AI tool's. Restructure piping to correctly capture the AI tool exit code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AI tool exit code is correctly captured in all three tool branches (amp, claude, opencode)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Hint: Use process substitution to avoid the leading echo pipe. For claude/opencode branches, the prompt can be passed via heredoc or <<<. For amp, use process substitution: timeout ... amp ... <<< "$PROMPT" 2>&1 | tee "$OUTFILE". Then PIPESTATUS[0] correctly captures the timeout/tool exit code, not echo's.
<!-- SECTION:NOTES:END -->
