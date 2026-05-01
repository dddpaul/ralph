---
id: TASK-71
title: Fix ralph-run watch loop to invoke /loop in dynamic mode
status: Done
assignee: []
created_date: '2026-05-01 07:17'
updated_date: '2026-05-01 07:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-70 implemented the watch loop with a contradiction between invocation and termination:

- `ralph-run` invokes `/loop <interval> /ralph-status-watch interval=<interval>` — **fixed-interval mode** (the harness controls timing).
- The watch skill terminates by NOT calling `ScheduleWakeup` for the next tick — but that mechanism only works in **dynamic mode** (`/loop` invoked without an interval).

Result: in fixed mode the harness keeps firing the watch every N minutes regardless of state. Terminal events (`completed`, `failed`, `crashed`, safety cap) are detected and surfaced, but the loop never actually stops — the user has to run `/loop stop` manually.

## Fix

Switch the invocation to **dynamic mode** by dropping the positional interval to `/loop`. The watch skill paces itself via `ScheduleWakeup` using the `interval` arg passed by `ralph-run`.

### `ralph-run` SKILL.md change

In Step 5 (\"If watch is set\"), replace:

```
Then invoke: `/loop <watch> /ralph-status-watch interval=<watch>`
```

with:

```
Then invoke: `/loop /ralph-status-watch interval=<watch>`
```

Note the absence of `<watch>` between `/loop` and the slash command — that's what triggers dynamic mode per Claude Code docs (\"Omit the interval to let the model self-pace\").

Update the surrounding prose to say \"dynamic-mode loop\" instead of fixed-interval, and adjust any mention of how often the watch fires (it's now self-paced via ScheduleWakeup at the configured interval).

### `ralph-status-watch` SKILL.md verification (no logic change expected)

Step 5 (\"Schedule Next Tick\") already calls `ScheduleWakeup` with `delaySeconds: interval_sec`. Verify this still works correctly under dynamic mode — it should, since ScheduleWakeup is exactly the dynamic-mode mechanism.

Also verify Step 4 (Safety Cap) still works: the tick count needs to be tracked across ScheduleWakeup-driven re-invocations. Per the existing skill, the tick count is read from the call chain or a counter convention. If the skill currently relies on /loop-injected tick metadata that's only available in fixed mode, switch to a self-tracked approach (e.g., pass `tick_count=N` in the next ScheduleWakeup prompt, increment on each entry).

### Documentation

Update `ralph-run` SKILL.md examples and any README mentions to reflect the dynamic-mode invocation. The user-facing semantics are unchanged: `watch=5m` still means \"poll every 5 minutes\" — only the mechanism changes.

## Smoke test

1. `/ralph-run watch=2m` on a quick task. Verify:
   - Watch fires within ~2 minutes of launch.
   - On completion, watch posts the full status block AND the loop ends (no further ticks fire).
   - `/ralph-status` after 5 minutes confirms no zombie polling.
2. `/ralph-run` (no watch) — unchanged hint behavior, no /loop invocation.
3. `/ralph-run watch=garbage` — still rejected with the existing actionable error.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-run SKILL.md Step 5 invokes /loop in dynamic mode (no positional interval to /loop): `/loop /ralph-status-watch interval=<watch>`
- [x] #2 ralph-run SKILL.md prose and examples updated to reflect dynamic-mode mechanism
- [x] #3 ralph-status-watch Safety Cap (Step 4) still terminates at 24 ticks under dynamic mode (tick count tracked via ScheduleWakeup arg or other self-tracking)
- [ ] #4 Smoke test: ralph-run watch=2m on a quick task — watch fires within ~2min, full status block on completion, NO further ticks after termination
- [ ] #5 Smoke test: ralph-run with no watch — hint message appears, no /loop invocation (regression)
- [ ] #6 Smoke test: ralph-run watch=garbage — rejected with existing actionable error (regression)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Fix ralph-run SKILL.md Step 5 to use dynamic-mode /loop invocation (drop positional interval). 2) Update prose/examples for dynamic-mode. 3) Verify ralph-status-watch safety cap works with tick_count passed via ScheduleWakeup prompt arg. 4) Update Step 4 in status-watch to use tick_count=N self-tracking via ScheduleWakeup prompt. 5) Smoke tests are manual UI tests - will note in task.

ACs 4-6 are smoke tests requiring interactive Claude Code sessions with ralph infrastructure. Cannot be automated — require manual verification.

Commit: `e5963ed` - task-71: Switch ralph-run watch loop to dynamic /loop mode

Commit: `af1c8e7` - task-71: Make Step 2 early-exit explicitly reference Step 5 tick_count

Implemented: switched /loop invocation from fixed-interval to dynamic mode, added tick_count self-tracking for safety cap. ACs 4-6 are interactive smoke tests requiring manual verification.
<!-- SECTION:NOTES:END -->
