---
id: TASK-101
title: >-
  Switch task-validator hook to PostToolUse JSON output
  (hookSpecificOutput.additionalContext)
status: Done
assignee: []
created_date: '2026-05-08 05:52'
updated_date: '2026-05-08 06:36'
labels: []
dependencies:
  - TASK-100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-100. Both `<system-reminder>` blocks in `.claude/hooks/task-validator.sh` use raw stdout text, which Claude Code's PostToolUse mechanism does NOT parse. Result: the model never receives validator output, even after TASK-100's wrapping fix.

## Verification (TASK-100 smoke test was insufficient)

TASK-100 AC #5 verified the script's stdout contains the right text. It did NOT verify the model actually receives it. Live test via `backlog task edit <id>` on a task with three identical ACs produces no model-visible system-reminder. Direct hook invocation (`echo ... | bash .claude/hooks/task-validator.sh`) prints the text to stdout but that is harness-internal — PostToolUse stdout outside the JSON protocol is dropped.

## Evidence

All other project hooks (`master-branch-guard.sh`, `naming-guard.sh`, `commit-msg-guard.sh`, `commit-prefix-guard.sh`, `notes-guard.sh`) emit JSON with `hookSpecificOutput` — they work. `task-validator.sh` is the odd one out using raw text.

## Required fix

Replace both blocks (det issues at lines ~134-141, LLM rubric at lines ~249-256) with a single JSON output of shape:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "<combined det issues + rubric text>"
  }
}
```

Combine logic:
- if RALPH_AUTONOMOUS=1 → emit nothing (exit 0 with no output)
- if det issues exist AND substantive → combine both into a single `additionalContext` string separated by a blank line
- if only det issues → just det block
- if only substantive → just rubric block
- if neither → emit nothing

Use `jq -n` or printf with proper JSON escaping. Watch for embedded newlines and backslashes in the `additionalContext` payload.

## Template parity (R11)

Apply identical fix to `skills/ralph-init/templates/claude/hooks/task-validator.sh`.

## Validation

After the fix, an `backlog task edit <id>` on a task with duplicate ACs MUST cause the model in the same session to receive a `<system-reminder>` containing 'Task validator [det] issues'. Verify by:

1. Create scratch task with `backlog task create "x" --ac dup --ac dup`.
2. Edit it: `backlog task edit <id> --append-notes trigger`.
3. Confirm the model context now includes additionalContext from the validator.
4. Archive scratch task.

## Reviewer hardening

Add a new rule (R15?) to `.claude/task-reviewer-rules.md`: PostToolUse hooks MUST emit JSON via `hookSpecificOutput.additionalContext` for model-visible feedback. Raw stdout text (including text wrapped in `<system-reminder>` tags) is dropped by the harness and MUST be rejected on review. This would have caught TASK-100.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Both validator output blocks (det issues and LLM rubric) emit JSON with hookSpecificOutput.additionalContext, replacing the raw <system-reminder> text
- [x] #2 When both det issues and substantive rubric apply, output is a single JSON object with combined additionalContext (not two separate JSON emissions)
- [x] #3 RALPH_AUTONOMOUS=1 still produces zero output (no JSON, no text)
- [x] #4 Live verification: backlog task edit on a task with duplicate ACs causes the model to receive a system-reminder containing the validator text in the same session
- [x] #5 Template parity: skills/ralph-init/templates/claude/hooks/task-validator.sh updated identically
- [x] #6 Add rule R15 to .claude/task-reviewer-rules.md requiring JSON output for PostToolUse hooks; raw stdout (including <system-reminder> tags) is review failure
- [x] #7 Bash syntax check passes (bash -n .claude/hooks/task-validator.sh and the template)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Replace both raw system-reminder printf blocks with single JSON output using jq -n + hookSpecificOutput.additionalContext. (2) Combine det+rubric into single additionalContext when both apply. (3) RALPH_AUTONOMOUS=1 still exits with no output. (4) Apply same fix to template. (5) Add R15 to task-reviewer-rules.md. (6) bash -n check both files.

Commit: `2168d54` - task-101: Switch task-validator hook to PostToolUse JSON output

task-reviewer APPROVED. All 7 ACs verified. Live test confirmed model receives additionalContext via PostToolUse JSON protocol.
<!-- SECTION:NOTES:END -->
