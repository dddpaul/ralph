---
id: TASK-135
title: >-
  Pause Ralph loop when ccusage shows 5h block ends within
  --block-end-buffer-min
status: Done
assignee: []
created_date: '2026-06-12 04:47'
updated_date: '2026-06-12 09:20'
labels:
  - 'feature:ralph-usage-cap'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A long Ralph autonomous run that starts a task with only a few minutes left in the Claude Code 5h block will likely be killed mid-task when the block resets — the next `claude --print` call may hit a hard rate-limit error and partial work is wasted. Use ccusage to read when the active 5h block ends, and pause the loop cleanly before that boundary so Ralph never picks up a task it cannot finish in the remaining window.

The pause is operator-resumable via re-running `/ralph-run`. No auto-resume — that would block heartbeats and confuse ralph-status-watch into declaring a crash.

## Architecture (full detail in design/ralph-usage-cap-brainstorm.md + two Addenda — read first)

Two hook points share one helper:

- Preflight: `skills/ralph-run/scripts/preflight.sh` calls `usage-check.sh` once before launch. Exit 1 refuses launch with the reason string. Exit 2 (cannot measure) warns and continues, writing `backlog/.ralph-usage-check-disabled` so per-iteration warns stay quiet.
- Per-iteration: `ralph.sh` main loop calls `usage-check.sh` at the top of each iteration body, before the existing `timeout … claude --print …` line (around L696). Exit 1 sets STATE=paused, populates PAUSED_REASON / PAUSED_BUFFER_MIN / PAUSED_REMAINING_MIN / PAUSED_BLOCK_END_TIME / PAUSED_AT, and breaks the loop. Exit 2 continues silently if the disabled flag exists, else warns once and writes the flag.

## New helper signature

```bash
# skills/ralph-run/scripts/usage-check.sh
# $1 = BUFFER_MIN    (integer >= 0; 0 disables the check entirely)
# Exit 0 → buffer=0 disabled, OR no active block, OR remainingMinutes > buffer
# Exit 1 → active block AND remainingMinutes <= buffer
#          prints "block_end_in_<rem>min_below_<buffer>min_buffer" to stdout
# Exit 2 → cannot measure (ccusage missing, jq/date missing, ccusage nonzero,
#          JSON unparseable, endTime field missing or malformed)
```

MODEL is no longer an arg — block boundaries are model-agnostic.

ccusage CLI invocation (verified against ccusage 20.1.0):

```bash
ccusage blocks --active --token-limit max --json
# returns:
# { "blocks": [ { "isActive": true, "isGap": false,
#                 "endTime": "2026-06-12T08:00:00.000Z",
#                 "models": ["claude-opus-4-7"], ... } ] }
# helper reads:  jq '.blocks[0].isActive', '.blocks[0].isGap',
#                jq -r '.blocks[0].endTime'
# remainingMinutes = (endTime - now) / 60
```

`--token-limit max` is irrelevant for time-based logic but harmless; kept for forward compatibility if future ccusage versions surface plan quotas. No-active-block (isActive=false or isGap=true) exits 0 — Ralph is not currently in a 5h window, so the boundary check does not apply.

## Status file delta

```jsonc
{
  "state": "paused",                                          // new value alongside running/completed/failed
  "paused_reason": "block_end_in_12min_below_30min_buffer",   // grep-friendly, no spaces
  "paused_buffer_min": 30,                                     // echo of --block-end-buffer-min
  "paused_remaining_min": 12,                                  // ccusage value at trip
  "paused_block_end_time": "2026-06-12T08:00:00Z",             // ccusage blocks[0].endTime
  "paused_at": "<ISO 8601 UTC when ralph paused>"
}
```

## ralph.sh flag

```
--block-end-buffer-min <N>   Pause when the active 5h block ends in <= N
                             minutes. Default: 0 (check disabled — no ccusage
                             invocation). No subscription-tier knowledge needed:
                             this only guards the block boundary, not cumulative
                             quota drain.
```

Mirror byte-identical in `skills/ralph-init/templates/root/ralph.sh` per R11 parity.

## ralph-init template allowlist (settings.local.json jq-merge fragment)

Add two PreToolUse-allow rules:

- `Bash(ccusage:*)`
- `Bash(./skills/ralph-run/scripts/usage-check.sh:*)`

## Out of scope (deliberate)

- Cumulative quota drain inside a block — not detected by boundary heuristic; add as a co-trigger only if it bites in practice.
- Auto-resume / sleep-until-next-block.
- Env-var fallback (`RALPH_BLOCK_END_BUFFER_MIN`).
- Token / dollar / percentage caps — explicitly rejected; see brainstorm Addenda for full rationale.
- Auto-installing ccusage in the devcontainer Dockerfile — fail-open with warning instead.
- Weekly window check — ccusage 20.1.0 exposes no weekly quota field.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 New file skills/ralph-run/scripts/usage-check.sh exists, takes single $1=BUFFER_MIN arg (integer >= 0), exits 0 (buffer=0 disabled, OR no active block / isGap=true / isActive=false, OR remainingMinutes > buffer), 1 (active block AND remainingMinutes <= buffer; prints block_end_in_<rem>min_below_<buffer>min_buffer to stdout), or 2 (cannot measure — ccusage missing, jq/date missing, ccusage nonzero, JSON unparseable, endTime field missing or malformed)
- [x] #2 ralph.sh accepts new --block-end-buffer-min <N> flag (default 0 = disabled, integer >= 0); the value 0 short-circuits the check entirely (no ccusage invocation); flag mirrored byte-identical in skills/ralph-init/templates/root/ralph.sh per R11 parity
- [x] #3 skills/ralph-run/scripts/preflight.sh invokes usage-check.sh with BUFFER_MIN; exit 1 refuses launch with the reason string; exit 2 writes a single stderr warning, creates backlog/.ralph-usage-check-disabled flag file, then continues; BUFFER_MIN=0 means preflight does not invoke ccusage at all (no helper call, no warning)
- [x] #4 ralph.sh main loop calls usage-check.sh at top of each iteration body before the existing timeout/claude invocation; exit 1 sets STATE=paused and populates PAUSED_REASON/PAUSED_BUFFER_MIN/PAUSED_REMAINING_MIN/PAUSED_BLOCK_END_TIME/PAUSED_AT then breaks the loop; exit 2 continues silently if the disabled-flag file already exists, otherwise warns once and creates the flag
- [x] #5 backlog/.ralph-status.json gains five fields populated only when state=paused: paused_reason (string like block_end_in_12min_below_30min_buffer), paused_buffer_min (integer), paused_remaining_min (integer), paused_block_end_time (ISO 8601 UTC from ccusage), paused_at (ISO 8601 UTC when ralph paused); existing state-machine paths (completed/failed/running) unchanged
- [x] #6 skills/ralph-status/SKILL.md renders an extra line when state=paused: 'Paused:  block ends in Xm (buffer Ym)' followed by a 'resume with /ralph-run' hint
- [x] #7 skills/ralph-status-watch terminates the watch loop when state=paused (treat as clean terminal state alongside completed/failed); does NOT declare crash via heartbeat staleness
- [x] #8 skills/ralph-init template settings.local.json jq-merge fragment gains two PreToolUse-allow rules: Bash(ccusage:*) and Bash(./skills/ralph-run/scripts/usage-check.sh:*)
- [x] #9 New file tests/unit/usage-check.bats covers at minimum: buffer=0 short-circuit (exit 0 without invoking PATH-mocked ccusage), no-active-block (isActive=false) exits 0, gap-block (isGap=true) exits 0, remaining-above-buffer pass (exit 0), remaining-at-or-below-buffer fail (exit 1), ccusage-missing exit-2, jq-missing exit-2, ccusage-nonzero exit-2, malformed-JSON exit-2, endTime-field-missing exit-2
- [x] #10 New file tests/integration/usage-pause.bats covers at minimum: preflight refuses launch when usage-check returns 1, preflight warns and continues when usage-check returns 2 plus creates the disabled-flag file, ralph.sh loop sets state=paused and breaks when mid-loop usage-check returns 1, per-iteration warn fires exactly once across multiple iterations when usage-check keeps returning 2
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-06-11 pivot to projection-based cap: ccusage 20.1.0 does not expose subscription quota percentage (verified empirically — blocks --json returns absolute tokens only, no used_percent field, --token-limit max only affects table warnings). Design switched to single flag --usage-cap-5h-tokens reading ccusage's projection.totalTokens (extrapolated 5h block total at current burn rate). Weekly window dropped from v1 scope. See design/ralph-usage-cap-brainstorm.md Addendum (added 2026-06-11) for full rationale.

2026-06-11 second pivot to time-based boundary heuristic: even projection-based token cap (--usage-cap-5h-tokens) bound to subscription-tier knowledge Anthropic does not publish (probed claude --help / claude -p /status / claude -p /cost / ccusage statusline / API rate-limit headers — all empty for plan-aware data). User picked option C: --block-end-buffer-min reading ccusage blocks[0].endTime. Sidesteps quota-knowledge entirely; only guards block boundary (does NOT detect cumulative drain inside block — explicit scope cut, can add token co-trigger later if needed). See design/ralph-usage-cap-brainstorm.md second Addendum (added 2026-06-11) for full rationale.

Starting implementation. Plan: 1) Create usage-check.sh helper with single BUFFER_MIN arg; 2) Add --block-end-buffer-min flag to ralph.sh (and mirror in template); 3) Wire into preflight.sh; 4) Wire into ralph.sh main loop with state=paused handling; 5) Update status renderers; 6) Add allowlist entries to ralph-init template; 7) Write bats unit + integration tests.

Commit: `65e31fb` - task-135: Add --block-end-buffer-min to pause Ralph before 5h block ends

Commit: `392dfc7` - task-135: Fix R12 contradiction in ralph-status-watch state enumeration

task-reviewer APPROVED on 2026-06-12. R12 contradiction in ralph-status-watch state enumeration was caught in first review pass and fixed in commit 392dfc7. R11 byte-identical parity verified across /workspace/ralph.sh, skills/ralph-run/scripts/ralph.sh, skills/ralph-init/templates/root/ralph.sh. All 17 new tests pass (12 unit + 5 integration). Full bats suite: 172 pass / 13 fail (all 13 pre-existing on master).
<!-- SECTION:NOTES:END -->
