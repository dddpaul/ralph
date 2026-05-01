---
id: TASK-70
title: Add ralph-status-watch skill with auto-start from ralph-run watch flag
status: To Do
assignee: []
created_date: '2026-05-01 06:30'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Today after `/ralph-run` launches Ralph in the background, the user must manually call `/ralph-status` to monitor progress. Add an opt-in auto-monitoring loop that surfaces only \"interesting\" events to the same conversation, polling at a user-configurable interval.

## Behavior

When user runs `/ralph-run watch=5m`, after a successful background launch the skill auto-invokes `/loop 5m /ralph-status-watch interval=5m`. Each tick reads `.ralph-status.json` + heartbeat mtime, detects events stateless-ly via timestamps in the file, and either stays silent (no event) or posts one message. Loop terminates when watch sees a terminal state OR after 24 ticks safety cap.

Default behavior (no `watch` arg) is unchanged — print the existing one-liner plus a hint about the new flag.

## ralph.sh changes (pre-requisite, all detection depends on this)

Add to `.ralph-status.json`:

1. **`iteration_started_at`** — ISO 8601 wall-clock timestamp written at the top of each iteration (alongside the existing `iteration` field). Cleared/updated when iteration changes.

2. **Restructure `errors[]`** — currently a list of strings. Change to a list of objects: `{\"iteration\": <int>, \"at\": <ISO timestamp>, \"message\": <string>}`. Update every code path that appends to `errors[]` to write the structured form.

3. **Update `ralph-status` skill consumer** — the existing `/ralph-status` skill prints errors. Verify it still renders correctly with the new object shape. If it currently does `errors[i]` as a string, update to read `.message`.

4. **Update unit/integration tests** that assert on `.ralph-status.json` shape.

## New skill: `~/.claude/skills/ralph-status-watch/SKILL.md` (or `skills/ralph-status-watch/SKILL.md`)

Description trigger: invoked by `/loop` only — not directly user-facing. Should NOT match common user phrases.

Args: `interval=<duration>` — passed through from `/ralph-run`. Used to scale detection windows.

Logic per tick:

1. Read `backlog/.ralph-status.json`. If missing → exit silently (loop will fire again or be cancelled).
2. Read heartbeat mtime: `stat -f %m backlog/.ralph-heartbeat 2>/dev/null || stat -c %Y backlog/.ralph-heartbeat 2>/dev/null`.
3. Apply detection rules in this order (first match wins):
   - **finished (e):** `state in {completed, failed}` → output full `/ralph-status`-style block. Set terminal flag.
   - **crashed (f):** `now - heartbeat_mtime > 15` AND `state == running` → output one-liner `Ralph: heartbeat stale > <Ns> — process likely crashed (PID <pid>)`. Set terminal flag.
   - **stuck (g):** `state == running` AND `(now - iteration_started_at)` in `[2*timeout_sec, 2*timeout_sec + interval_sec]` → output one-liner `Ralph: TASK-<id> stuck — iteration <n> running > <duration> (2× the <timeout>m timeout).`
   - **failed iteration (d):** any entry in `errors[]` with `at` in `[now - interval_sec, now]` → output one-liner per match: `Ralph: TASK-<id> — iteration <n> failed (<message>). Continuing.` Skip if a higher-priority event already fired.
   - Otherwise: silent.
4. Safety cap: if `--tick-count` >= 24, set terminal flag (regardless of state).
5. Termination: if terminal flag set, do NOT call `ScheduleWakeup` for the next tick (or whatever the dynamic-mode `/loop` contract requires to end the loop).

## ralph-run skill changes

1. Parse new `watch` arg. Validate value matches `^(true|false|[0-9]+(s|m|h))$`. Reject otherwise: `BLOCKED: watch must be true, false, or a duration like 5m, 30s, 1h.`
2. Normalize: `watch=true` → `5m`. `watch=false` or omitted → empty.
3. After successful launch (heartbeat verified):
   - If watch is empty: print existing one-liner plus a hint: `Hint: pass watch=5m to /ralph-run for automatic progress alerts.`
   - If watch is set: print the existing one-liner AND invoke `/loop <interval> /ralph-status-watch interval=<interval>` immediately.
4. Add `watch` row to the args table in SKILL.md with default and accepted values.
5. Add example invocations: `/ralph-run watch=5m`, `/ralph-run tasks=70 watch=2m max_iterations=3`.

## Out of scope
- Done-task tracking (explicitly dropped during brainstorm)
- Per-iteration heartbeat messages in chat
- Automatic `/ralph-stop` invocation on crash detection
- Side snapshot file at `backlog/.ralph-watch-state.json`

## Risks
- Missed-tick edge case for \"stuck\" detection (Claude busy when /loop fires). Mitigation if it bites: widen window to `2*tick_interval`.
- Default 5m interval lands exactly at the prompt cache TTL — acceptable trade-off.
- The errors[] shape change is a breaking change to .ralph-status.json. Any external consumer (e.g., a dashboard reading the file) will need to update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh writes iteration_started_at (ISO timestamp) to .ralph-status.json at the top of each iteration
- [ ] #2 ralph.sh writes errors[] as list of {iteration, at, message} objects (not bare strings)
- [ ] #3 Existing ralph-status skill still renders error messages correctly with the new object shape
- [ ] #4 Unit/integration tests asserting on .ralph-status.json shape are updated
- [ ] #5 New skill ralph-status-watch exists; reads .ralph-status.json + heartbeat; implements all 4 detection rules with first-match-wins precedence (e > f > g > d)
- [ ] #6 Watch outputs full status block on finished (e); one-liner on crashed/stuck/failed (f, g, d); silent otherwise
- [ ] #7 Watch terminates the loop on terminal state (e or f) OR at tick #24
- [ ] #8 ralph-run accepts watch arg; validates against regex ^(true|false|[0-9]+(s|m|h))$; rejects invalid with actionable error
- [ ] #9 ralph-run with watch=true normalizes to 5m; watch=false or omitted preserves today's hint-only behavior
- [ ] #10 ralph-run with watch=5m invokes /loop 5m /ralph-status-watch interval=5m after successful background launch
- [ ] #11 ralph-run SKILL.md args table and examples updated to document the watch arg
- [ ] #12 Smoke test: launch Ralph with watch=2m on a quick task; verify finished message appears with full status block; verify loop terminates
- [ ] #13 Smoke test: launch Ralph without watch; verify hint message appears; verify no /loop is invoked
- [ ] #14 Smoke test: ralph-run with watch=garbage rejected with actionable error message
<!-- AC:END -->
