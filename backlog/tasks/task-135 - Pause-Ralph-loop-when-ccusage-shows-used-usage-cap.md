---
id: TASK-135
title: Pause Ralph loop when ccusage shows used >= --usage-cap
status: To Do
assignee: []
created_date: '2026-06-12 04:47'
labels:
  - 'feature:ralph-usage-cap'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A long Ralph autonomous run cannot finish a task if the Claude Code subscription quota empties mid-task — the next `claude --print` call returns an error and partial work is wasted. Use ccusage to read used% on the active model's 5h and weekly windows, and pause the loop cleanly between iterations before that happens. Default cap is 80% used (= 20% remaining) per the user's directive.

The pause is operator-resumable via re-running `/ralph-run`. No auto-resume — that would block heartbeats and confuse ralph-status-watch into declaring a crash.

## Architecture (full detail in design/ralph-usage-cap-brainstorm.md — read first)

Two hook points share one helper:

- Preflight: `skills/ralph-run/scripts/preflight.sh` calls `usage-check.sh` once before launch. Exit 1 refuses launch with the reason string. Exit 2 (cannot measure) warns and continues, writing `backlog/.ralph-usage-check-disabled` so per-iteration warns stay quiet.
- Per-iteration: `ralph.sh` main loop calls `usage-check.sh` at the top of each iteration body, before the existing `timeout … claude --print …` line (around L696). Exit 1 sets STATE=paused, populates PAUSED_REASON / PAUSED_CAP / PAUSED_AT, and breaks the loop. Exit 2 continues silently if the disabled flag exists, else warns once and writes the flag.

## New helper signature

```bash
# skills/ralph-run/scripts/usage-check.sh
# $1 = MODEL          (e.g. claude-opus-4-7)
# $2 = USAGE_CAP      (integer percent, 0-100; 100 disables and skips ccusage)
# Exit 0 → both 5h and weekly used% < cap (proceed)
# Exit 1 → at least one window's used% >= cap (prints "usage_<window>_<model_short>_<pct>pct")
# Exit 2 → cannot measure (ccusage missing, jq missing, ccusage nonzero, JSON unparseable, no block for model)
```

ccusage CLI invocation assumed: `ccusage blocks --json` (verify at implementation time; if schema differs, helper absorbs it).

## Status file delta

```jsonc
{
  "state": "paused",                          // new value alongside running/completed/failed
  "paused_reason": "usage_5h_opus_82pct",     // grep-friendly, no spaces
  "paused_cap": 80,                            // echo of --usage-cap that tripped
  "paused_at": "<ISO 8601 UTC>"
}
```

## ralph.sh flag

```
--usage-cap <pct>   Pause when ccusage shows used >= pct% on 5h or weekly
                    window for the active model (default 80, range 0-100,
                    100 disables — short-circuits without calling ccusage).
```

Mirror byte-identical in `skills/ralph-init/templates/root/ralph.sh` per R11 parity.

## ralph-init template allowlist (settings.local.json jq-merge fragment)

Add two PreToolUse-allow rules:

- `Bash(ccusage:*)`
- `Bash(./skills/ralph-run/scripts/usage-check.sh:*)`

## Out of scope (deliberate)

- Auto-resume / sleep-and-wait.
- Env-var fallback (`RALPH_USAGE_CAP`).
- Per-window separate caps.
- Auto-installing ccusage in the devcontainer Dockerfile.
- Checking all models regardless of `--model` setting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 New file skills/ralph-run/scripts/usage-check.sh exists, takes $1=MODEL and $2=USAGE_CAP args, exits 0 (both windows below cap), 1 (cap tripped on at least one window; prints usage_<window>_<model_short>_<pct>pct to stdout), or 2 (cannot measure — ccusage/jq missing, ccusage nonzero, JSON unparseable, or no block for the active model)
- [ ] #2 ralph.sh accepts new --usage-cap <pct> flag (default 80, range 0-100 inclusive, where 100 means disabled and short-circuits without invoking ccusage); flag mirrored byte-identical in skills/ralph-init/templates/root/ralph.sh per R11 parity
- [ ] #3 skills/ralph-run/scripts/preflight.sh invokes usage-check.sh with MODEL and USAGE_CAP; exit 1 refuses launch with the reason string; exit 2 writes a single stderr warning, creates backlog/.ralph-usage-check-disabled flag file, then continues
- [ ] #4 ralph.sh main loop calls usage-check.sh at top of each iteration body before the existing timeout/claude invocation; exit 1 sets STATE=paused and populates PAUSED_REASON/PAUSED_CAP/PAUSED_AT then breaks the loop; exit 2 continues silently if the disabled-flag file already exists, otherwise warns once and creates the flag
- [ ] #5 backlog/.ralph-status.json gains three fields populated only when state=paused: paused_reason (string like usage_5h_opus_82pct), paused_cap (integer), paused_at (ISO 8601 UTC); existing state-machine paths (completed/failed/running) unchanged
- [ ] #6 skills/ralph-status/SKILL.md renders an extra line when state=paused: 'Paused:  usage <window> <model> XX% (cap YY%)' followed by a 'resume with /ralph-run' hint
- [ ] #7 skills/ralph-status-watch terminates the watch loop when state=paused (treat as clean terminal state alongside completed/failed); does NOT declare crash via heartbeat staleness
- [ ] #8 skills/ralph-init template settings.local.json jq-merge fragment gains two PreToolUse-allow rules: Bash(ccusage:*) and Bash(./skills/ralph-run/scripts/usage-check.sh:*)
- [ ] #9 New file tests/unit/usage-check.bats covers at minimum: above-cap pass (exit 0), 5h-below-cap fail (exit 1), weekly-below-cap fail (exit 1), ccusage-missing exit-2, jq-missing exit-2, ccusage-nonzero exit-2, malformed-JSON exit-2, no-block-for-model exit-2, --usage-cap 100 short-circuit verified by PATH-mocked ccusage that records whether it was invoked (must be: not invoked)
- [ ] #10 New file tests/integration/usage-pause.bats covers at minimum: preflight refuses launch when usage-check returns 1, preflight warns and continues when usage-check returns 2 plus creates the disabled-flag file, ralph.sh loop sets state=paused and breaks when mid-loop usage-check returns 1, per-iteration warn fires exactly once across multiple iterations when usage-check keeps returning 2
<!-- AC:END -->
