---
id: TASK-120
title: Fix false-positive 'not found' check in preflight.sh tasks_whitelist
status: In Progress
assignee: []
created_date: '2026-05-11 11:36'
updated_date: '2026-05-11 11:54'
labels:
  - 'feature:ralph-run'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Defect

skills/ralph-run/scripts/preflight.sh line 44 uses a loose substring match to detect missing tasks:

```bash
if [[ -z "$_wl_out" ]] || echo "$_wl_out" | grep -q "not found"; then
```

The grep `"not found"` matches anywhere in the backlog output. Task descriptions that legitimately contain the phrase 'not found' (e.g., 'if heading not found, treat as legacy') trigger this check and cause preflight to refuse to launch Ralph for a task that exists and is in To Do state.

## Witnessed

2026-05-11 on TASK-119: description contained 'if heading not found, treat entire existing file as user content...' in AC #5. Preflight returned:

```
ERROR: TASK-119 not found in backlog
```

Workaround was to rephrase AC #5 to use 'absent' instead of 'not found' — masks the bug, doesn't fix it.

## Root cause

`backlog task <id> --plain` returns:
- For existing task: the task body (full description, including any 'not found' substring)
- For missing task: the single line `Task <id> not found.` (with period), exit code 0

The script can't use exit code (always 0) but CAN distinguish via the canonical error line shape.

## Fix proposal

Replace line 44 substring match with an anchored regex match against the canonical backlog error line:

```bash
if [[ -z "$_wl_out" ]] || echo "$_wl_out" | grep -qE "^Task [0-9]+ not found\\.$"; then
```

Anchors (`^` and `$`) + literal period escape ensure the match only triggers on the actual error line, never on text embedded in a task description.

## Source files

- `skills/ralph-run/scripts/preflight.sh` (line 44) — project copy, source of truth
- `~/.claude/skills/ralph-run/scripts/preflight.sh` — user-global copy, refreshed by ralph-sync after the project copy is merged
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-run/scripts/preflight.sh line ~44 uses an anchored regex 'grep -qE "^Task [0-9]+ not found\.$"' instead of the loose substring 'grep -q "not found"'
- [x] #2 After the fix, running 'bash skills/ralph-run/scripts/preflight.sh ./ralph.sh true --tasks <id>' on a real existing To Do task whose description contains the phrase 'not found' returns 'OK RALPH_PATH=...' (no false ERROR)
- [x] #3 After the fix, running 'bash skills/ralph-run/scripts/preflight.sh ./ralph.sh true --tasks 99999' (nonexistent id) still returns 'ERROR: TASK-99999 not found in backlog'
- [x] #4 bash -n skills/ralph-run/scripts/preflight.sh passes (no syntax error)
- [ ] #5 After merge and ralph-sync, 'bash .claude/skills/ralph-sync/sync.sh classify' shows skill ralph-run as [unchanged]
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fix applied: preflight.sh line 44 substring 'not found' replaced with anchored regex '^Task [0-9]+ not found\.$'. ACs 2/3/4 verified via direct test. AC 1 verified by grep. AC 5 (post-merge ralph-sync) pending.

Commit: `a23608f` - task-120: Anchor preflight not-found check to canonical error line

Reviewer APPROVED (a23608f) on second pass after reverting unrelated brainstorm-rules.md drift.
<!-- SECTION:NOTES:END -->
