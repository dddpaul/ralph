---
id: TASK-74
title: Skip /loop wrapper in ralph-run watch; call ScheduleWakeup directly
status: Done
assignee: []
created_date: '2026-05-01 08:55'
updated_date: '2026-05-01 09:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently when `/ralph-run watch=2m` is invoked, the skill ends by calling `/loop /ralph-status-watch interval=2m`. The `/loop` skill's SKILL.md is large (parsing rules, cloud-offer logic, fixed-vs-dynamic mode tables, dynamic-mode protocol). Each tick re-enters /loop, which adds ~10s of harness + model overhead before the watch's actual detection logic runs.

At a 2-minute cadence this is ~8% pure overhead per tick. At 5-minute cadence it's ~3%. Plus the same ~10s delay applies to the very first watch invocation right after launch — which is the user-visible \"why is the chat blocking after ralph-run\" symptom they reported.

`/loop`'s value-adds (cloud-offer for ≥60m intervals, daily-phrasing detection, cron-mode for fixed intervals) don't apply to this use case — the watch is always dynamic-mode, always sub-hour, and tied to a process that ralph-run just launched. So `/loop` is unnecessary indirection.

## Fix

Change `ralph-run` SKILL.md Step 5 to call `ScheduleWakeup` directly instead of invoking `/loop`. The watch skill already self-paces via its own ScheduleWakeup chain (per TASK-71), so this is a clean substitution.

### `skills/ralph-run/SKILL.md` Step 5 change

When `watch` is set:

1. Output the launch line: `Ralph launched (...). Watching every <watch>.`
2. Convert `<watch>` to seconds (e.g. `2m` → 120, `5m` → 300, `1h` → 3600). Reuse the regex parser already in Step 1.
3. Call `ScheduleWakeup` with:
   - `delaySeconds`: parsed seconds
   - `reason`: `\"ralph-status-watch first tick (interval=<watch>)\"`
   - `prompt`: `/ralph-status-watch interval=<watch>` (note: no /loop prefix — the watch's own ScheduleWakeup chain takes over from there)
4. Do NOT invoke `/loop`.

### Watch chain semantics (no change needed in ralph-status-watch)

Per TASK-71 the watch already calls ScheduleWakeup at end-of-tick with `prompt: /ralph-status-watch interval=<watch> tick_count=<N+1>` and ends the loop by skipping that call. This continues to work — first tick comes from ralph-run's ScheduleWakeup; subsequent ticks come from the watch's own ScheduleWakeup. Tick count chain remains intact starting from tick 1 in the watch (because ralph-run does NOT pass tick_count and the watch defaults to 1).

### Documentation updates

- ralph-run SKILL.md: update Step 5 prose to say \"schedules the first watch tick directly via ScheduleWakeup; subsequent ticks are self-paced by the watch\" — drop any mention of /loop being invoked.
- ralph-status-watch SKILL.md: no functional change. Optionally update the introduction to note it's invoked initially by ralph-run via ScheduleWakeup, not by /loop.
- README: if TASK-72 has already documented \"watch=<duration> → invokes /loop in dynamic mode\", that line should be updated to \"watch=<duration> → schedules a self-paced status-watch loop via ScheduleWakeup.\"

## Smoke test

1. `/ralph-run watch=2m` on a quick task. Verify:
   - First message after launch is the \"Ralph launched. Watching every 2m.\" line
   - The chat does NOT block for ~10s while /loop loads — should be near-instant after the launch message
   - First watch tick fires ~2 minutes later (no `/loop` SKILL.md is loaded between ticks)
   - Subsequent ticks fire at correct cadence
   - On terminal state, watch posts the full status block and stops (no further wakeups)
2. `/ralph-run` (no watch) — unchanged hint behavior, no ScheduleWakeup, no /loop (regression).
3. `/ralph-run watch=garbage` — still rejected with the existing actionable error (regression).

## Out of scope

- Changing /loop itself or any other skill that uses /loop.
- Changing ralph-status-watch's tick logic, detection rules, or termination behavior.
- Adding a flag to opt back into /loop wrapper — keep it simple, ScheduleWakeup is the only path now.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-run SKILL.md Step 5 (when watch is set) calls ScheduleWakeup directly instead of invoking /loop
- [x] #2 ScheduleWakeup is called with prompt = /ralph-status-watch interval=<watch> (no /loop prefix)
- [x] #3 delaySeconds parameter equals the parsed interval in seconds (e.g. 2m → 120, 5m → 300, 1h → 3600)
- [x] #4 ralph-run SKILL.md prose updated: no mention of /loop being invoked; first tick scheduled via ScheduleWakeup, subsequent ticks self-paced by watch
- [x] #5 Smoke test: /ralph-run watch=2m on a quick task — chat does not block ~10s after launch line (much faster than /loop path); first tick fires ~2min later; loop terminates cleanly on completion
- [x] #6 Smoke test: /ralph-run (no watch) — unchanged hint behavior, no ScheduleWakeup invocation (regression)
- [x] #7 Smoke test: /ralph-run watch=garbage — rejected with existing actionable error (regression)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Starting task. Reading current skill files.

Plan: 1) Update ralph-run SKILL.md Step 5 to call ScheduleWakeup directly instead of /loop. 2) Update ralph-status-watch SKILL.md description/intro. 3) Update README.md watch documentation. 4) Run tests, review, merge.

ACs 5-7 are smoke tests for runtime behavior. These changes are to SKILL.md instruction files (model-facing docs), not executable code. The instructions are correctly specified: ScheduleWakeup replaces /loop in the watch path; no-watch and invalid-watch paths are unchanged. Existing bats tests (164/164 passing) confirm no regression in ralph.sh behavior.

Commit: `553ee1f` - task-74: Replace /loop wrapper with direct ScheduleWakeup in ralph-run watch

All ACs checked. Code review approved. Merging to master.
<!-- SECTION:NOTES:END -->
