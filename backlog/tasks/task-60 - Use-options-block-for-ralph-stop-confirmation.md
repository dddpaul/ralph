---
id: TASK-60
title: Use options block for ralph-stop confirmation
status: Done
assignee:
  - '@claude'
created_date: '2026-04-25 09:09'
updated_date: '2026-04-25 10:07'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace the inline [y/N] text prompt in skills/ralph-stop/SKILL.md Step 4 with the harness <options> block so the user can confirm with one click instead of typing.

## Context

Currently ralph-stop Step 4 instructs Claude to output:

Stop Ralph (PID <pid>) at iteration <iteration> of <max_iterations>, current task: <current_task>? [y/N]

The user must type y or n. The harness supports an <options> block that renders clickable buttons. This is documented in CLAUDE.md / project conventions: end the response with an <options> block on its own lines, not inside any other text or codeblock.

## Files involved

- skills/ralph-stop/SKILL.md — Step 4 only

## New behavior

Step 4 instructs Claude to:
1. Output a one-line status header showing PID, iteration N of M, and current task
2. End the response with an <options> block:

<options>
<option>Stop Ralph</option>
<option>Cancel</option>
</options>

Step 5 onward (graceful shutdown, force kill, report) stays unchanged. The user's choice is interpreted on the next turn: 'Stop Ralph' → proceed; anything else → output Cancelled. and stop.

## Out of scope

ralph-run and ralph-status do not need confirmation prompts — leave them alone.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-stop/SKILL.md Step 4 replaces the [y/N] line with an <options> block containing 'Stop Ralph' and 'Cancel'
- [x] #2 Step 4 still shows PID, current iteration, max iterations, and current task before the options block
- [x] #3 <options> block is on its own lines at the very end of the response, not nested inside other text or a codeblock
- [x] #4 On 'Cancel' (or any non-'Stop Ralph' reply), Claude outputs 'Cancelled.' and stops without sending any signals
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Replace Step 4's [y/N] text prompt with a status header line followed by an <options> block. Add instruction that 'Stop Ralph' proceeds to Step 5, anything else outputs 'Cancelled.' and stops.

Commit: `7a6aca0` - task-60: Use options block for ralph-stop confirmation

Replaced [y/N] text prompt in Step 4 with <options> block containing 'Stop Ralph' and 'Cancel'. Added next-turn interpretation instructions. Files changed: skills/ralph-stop/SKILL.md
<!-- SECTION:NOTES:END -->
