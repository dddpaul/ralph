---
id: TASK-128
title: >-
  Extend ralph-init template allowlist with missing Skill and ScheduleWakeup
  rules
status: To Do
assignee: []
created_date: '2026-05-19 08:44'
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
- [ ] #1 templates/claude/settings.local.json .permissions.allow array contains exactly these new entries: Skill(ralph-status-watch), Skill(ralph-task), Skill(ralph-init), ScheduleWakeup
- [ ] #2 Existing entries in the template (Skill(ralph-run), Skill(ralph-status), Skill(ralph-stop), Skill(brainstorm), etc.) remain unchanged
- [ ] #3 jq -r '.permissions.allow | length' on the template shows count = old count + 4
- [ ] #4 Smoke test on a freshly ralph-init'd project: /ralph-run tasks=N watch=5m completes one tick (5+ minutes) without firing a permission prompt for Skill(ralph-status-watch) or ScheduleWakeup
<!-- AC:END -->
