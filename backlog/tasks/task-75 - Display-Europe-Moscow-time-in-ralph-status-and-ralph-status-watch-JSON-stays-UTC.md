---
id: TASK-75
title: >-
  Display Europe/Moscow time in ralph-status and ralph-status-watch (JSON stays
  UTC)
status: Done
assignee: []
created_date: '2026-05-01 10:05'
updated_date: '2026-05-01 10:22'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
.ralph-status.json stores all timestamps in UTC ISO 8601 with `Z` suffix (e.g. `2026-05-01T08:50:16Z`). The user wants to read these in Europe/Moscow time when surfaced through `/ralph-status` and `/ralph-status-watch`. Convert in the display layer only — JSON shape and ralph.sh writes are unchanged (backward-compatible for any external consumer).

## Scope

### `skills/ralph-status/SKILL.md`

Convert UTC fields to Europe/Moscow time when displaying:
- `Completed at: <completed_at>` — convert UTC ISO to Moscow format like `2026-05-01 11:53:21 MSK` (or ISO-style `2026-05-01T11:53:21+03:00 (MSK)`).
- Anywhere `started_at` is shown to the user (currently it's only used for elapsed-time math, not displayed — verify and update if displayed).
- Errors: each error has an `at` ISO timestamp. If the skill displays it (currently `at` is described as 'available but not displayed'), and if a future change displays it, convert to Moscow.

Conversion mechanic (bash): `TZ=Europe/Moscow date -j -f \"%Y-%m-%dT%H:%M:%SZ\" \"$utc_iso\" \"+%Y-%m-%d %H:%M:%S MSK\"` on macOS BSD; or `TZ=Europe/Moscow date -d \"$utc_iso\" \"+%Y-%m-%d %H:%M:%S MSK\"` on GNU. Skill should pick the right form or use a portable approach.

### `skills/ralph-status-watch/SKILL.md`

Rule (e) Finished — outputs the full status block on terminal state. Apply the same Moscow conversion to `Completed at:` line in that block. Same conversion mechanic.

Other rules (d failed iteration, f crashed, g stuck) currently emit one-liners without raw timestamps. If a future change adds timestamps to these, apply the same conversion.

### Time math (NOT changed)

- `current_time - heartbeat_mtime` for liveness — pure epoch arithmetic, no timezone involved
- `current_time - started_at` for elapsed — convert started_at_iso → epoch via `date`; epoch is timezone-agnostic
- Stuck detection window — same epoch arithmetic

These already work correctly regardless of display timezone.

### `ralph.sh` — NO change

Writes to `.ralph-status.json` stay UTC (`date -u +%Y-%m-%dT%H:%M:%SZ`). External consumers reading the JSON continue to see UTC.

## Smoke test

1. Trigger a quick Ralph run that completes within a few minutes.
2. After completion, run `/ralph-status` — verify `Completed at:` shows Moscow time (offset +03:00, label MSK or +03 marker).
3. Verify the underlying `.ralph-status.json` `completed_at` field is still UTC (`Z` suffix).
4. Run `/ralph-status` while Ralph is mid-run — verify any displayed timestamps are Moscow.
5. Run watch with `/ralph-run watch=2m` on a quick task — verify the full status block on completion shows Moscow times.

## Out of scope

- Configurable timezone (hardcoded Europe/Moscow per user's request)
- Changing JSON storage format (option A from brainstorm — explicitly rejected)
- ralph.sh changes
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-status SKILL.md converts completed_at and any other displayed UTC timestamps to Europe/Moscow time
- [x] #2 ralph-status-watch SKILL.md Rule (e) full status block converts completed_at to Europe/Moscow time
- [x] #3 Conversion mechanic is portable (works on macOS BSD date and GNU date)
- [x] #4 .ralph-status.json content unchanged — completed_at, started_at, iteration_started_at, errors[].at all remain UTC with Z suffix
- [x] #5 ralph.sh source unchanged
- [x] #6 Time math (heartbeat liveness, elapsed, stuck detection) continues to work correctly using epoch arithmetic
- [ ] #7 Smoke test: /ralph-status after a quick run shows Moscow time in Completed at; underlying JSON is still UTC
- [ ] #8 Smoke test: /ralph-run watch=2m on a quick task — terminal status block shows Moscow time
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Starting task. Will modify display layer in ralph-status and ralph-status-watch skills to convert UTC to Europe/Moscow time.

Plan: Add a UTC-to-Moscow conversion instruction block in ralph-status SKILL.md (Step 3, Completed at line) and ralph-status-watch SKILL.md (Rule e, Completed at line). Use portable date conversion: try GNU date -d first, fall back to BSD date -j. Hardcode Europe/Moscow (+03:00 / MSK).

Commit: `95f3e17` - task-75: Display Europe/Moscow time in ralph-status and ralph-status-watch

Implementation complete. Conversion verified: UTC 08:50:16Z -> 2026-05-01 11:50:16 MSK. Code review approved. AC 7-8 (smoke tests) require a live Ralph run for manual verification.
<!-- SECTION:NOTES:END -->
