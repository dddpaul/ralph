---
id: TASK-1
title: Fix PIPESTATUS bug in ralph.sh
status: Done
assignee:
  - '@claude'
created_date: '2026-04-16 07:52'
updated_date: '2026-04-17 07:53'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
EXIT_CODE=${PIPESTATUS[0]} after echo | timeout ... | tee may capture echo's exit code, not the AI tool's. Restructure piping to correctly capture the AI tool exit code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AI tool exit code is correctly captured in all three tool branches (amp, claude, opencode)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Hint: Use process substitution to avoid the leading echo pipe. For claude/opencode branches, the prompt can be passed via heredoc or <<<. For amp, use process substitution: timeout ... amp ... <<< "$PROMPT" 2>&1 | tee "$OUTFILE". Then PIPESTATUS[0] correctly captures the timeout/tool exit code, not echo's.

Plan: Replace 'echo $PROMPT | timeout ... tool | tee' with 'timeout ... tool <<< $PROMPT | tee' for all three branches (amp, claude, opencode). This eliminates the leading echo from the pipeline, making PIPESTATUS[0] capture the AI tool exit code instead of echo's. For opencode, which takes a positional argument, keep the current structure but fix PIPESTATUS index. Actually opencode uses 'run $PROMPT' so no pipe needed there — but still uses PIPESTATUS[0] which is correct since it's a 2-element pipeline already. Will verify each branch.

Commit: `0e67bdd` - task-1: Capture AI tool exit code instead of echo exit code

Replaced 'echo $PROMPT | timeout ... tool | tee' with 'timeout ... tool <<< $PROMPT | tee' in amp and claude branches. opencode branch was already correct (no leading echo pipe). This makes PIPESTATUS[0] capture the AI tool exit code. Files changed: ralph.sh
<!-- SECTION:NOTES:END -->
