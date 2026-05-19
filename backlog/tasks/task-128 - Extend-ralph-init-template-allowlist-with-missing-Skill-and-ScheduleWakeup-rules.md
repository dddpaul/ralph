---
id: TASK-128
title: >-
  Extend ralph-init template allowlist with missing Skill and ScheduleWakeup
  rules
status: Done
assignee: []
created_date: '2026-05-19 08:44'
updated_date: '2026-05-19 11:28'
labels: []
dependencies:
  - TASK-127
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Split from TASK-127 (Section A + B). After a fresh `/ralph-init`, every `/ralph-run watch=5m` tick fires a permission prompt for `Skill(ralph-status-watch)` and `ScheduleWakeup` — both are core mechanism of the watch loop and ship outside the template allowlist. Same prompt-thrash applies on every `/ralph-task` invocation and every `ralph upgrade` (`Skill(ralph-init)`).

## Scope

`skills/ralph-init/templates/claude/settings.local.json` allowlist additions:

- `Skill(ralph-status-watch)` — self-scheduled by `ralph-run` every `watch` interval, NOT user-facing, but currently prompts each tick
- `Skill(ralph-task)` — ad-hoc task creation / edit-deliberation
- `Skill(ralph-init)` — upgrade flow (`ralph upgrade`)
- `ScheduleWakeup` — the literal deferred tool that drives the watch chain (highest pain point per TASK-127 Section B)

## Out of scope

- `TaskCreate`, `TaskUpdate`, etc — harness-built-ins, may or may not need explicit allow depending on user's claude-code version; left for follow-up.
- `mcp__happy__change_title` — third-party MCP, not stock Ralph.
- pptx-related skills — covered by sibling task 127d.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 templates/claude/settings.local.json .permissions.allow array contains exactly these new entries: Skill(ralph-status-watch), Skill(ralph-task), Skill(ralph-init), ScheduleWakeup
- [x] #2 Existing entries in the template (Skill(ralph-run), Skill(ralph-status), Skill(ralph-stop), Skill(brainstorm), etc.) remain unchanged
- [x] #3 jq -r '.permissions.allow | length' on the template shows count = old count + 4
- [ ] #4 Smoke test on a freshly ralph-init'd project: /ralph-run tasks=N watch=5m completes one tick (5+ minutes) without firing a permission prompt for Skill(ralph-status-watch) or ScheduleWakeup
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add exactly 4 entries to templates/claude/settings.local.json .permissions.allow: Skill(ralph-status-watch), Skill(ralph-task), Skill(ralph-init), ScheduleWakeup. Preserve all 26 existing entries unchanged (new count=30). Append after Skill(brainstorm) to keep Skill entries grouped. Verify with jq length. AC#4 is a 5+ min live smoke test on a fresh ralph-init project — assess feasibility in autonomous sandbox; document if manual verification required.

AC #1-3 verified: jq confirms .permissions.allow length=30 (was 26, +4); the 4 new entries present (Skill(ralph-status-watch), Skill(ralph-task), Skill(ralph-init), ScheduleWakeup); all 26 prior entries unchanged in original positions (new entries appended after Skill(brainstorm)). JSON validated by jq parse. Full bats suite run: only pre-existing flaky failure #158 'Temp file cleaned up on timeout' in timeout-handling.bats; confirmed unrelated since git diff master..HEAD -- ralph.sh tests/ = 0 lines (code under test byte-identical to master). AC #4 (5+ min live /ralph-run watch=5m smoke test observing no permission prompt) cannot be executed in a single autonomous sandbox iteration: the loop completes one task then stops and cannot observe interactive permission prompts. Static verification instead: new rule strings use the exact canonical permission identifiers — Skill(name) form and bare ScheduleWakeup tool name — identical in shape to the already-working Skill(ralph-run)/Skill(brainstorm) entries, so the harness literal match will allow them. AC #4 deferred for manual verification on a fresh ralph-init project.

Commit: `8d7dda0` - task-128: Add Skill(ralph-status-watch), Skill(ralph-task), Skill(ralph-init), ScheduleWakeup to ralph-init template allowlist

Correction: re-run shows test #158 'Temp file cleaned up on timeout' fails CONSISTENTLY (2/2 runs), not flaky — a pre-existing bug in ralph.sh timeout temp-file cleanup, unrelated to and out of scope for TASK-128 (git diff master..HEAD -- ralph.sh tests/ = 0 lines; code under test byte-identical to master). task-reviewer agent verdict: APPROVED — AC #1-3 verified from git objects, AC #4 deferral accepted per rule R2 with TASK-126 precedent, R6/R11/R13 clean. Marking Done.
<!-- SECTION:NOTES:END -->
