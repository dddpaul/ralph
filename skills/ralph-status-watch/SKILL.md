---
name: ralph-status-watch
description: "Internal skill for monitoring Ralph progress. Reads .ralph-status.json + heartbeat, detects events, and terminates the loop on completion. Initially scheduled by ralph-run via ScheduleWakeup; subsequent ticks are self-paced."
---

# Ralph Status Watch (internal)

Monitor a running Ralph agent and surface interesting events. Initially invoked by `ralph-run` via `ScheduleWakeup`; subsequent ticks are self-paced via the skill's own `ScheduleWakeup` chain. Not directly user-facing.

---

## Step 1: Parse Arguments

Extract from skill args:
- `interval=<duration>` — the polling interval passed through from `/ralph-run`
- `tick_count=<N>` — the current tick number (self-tracked across invocations)

Parse the duration into seconds (`interval_sec`):
- `Ns` or just `N` → N seconds
- `Nm` → N * 60 seconds
- `Nh` → N * 3600 seconds

Default: `interval_sec = 300` (5 minutes) if not provided or unparseable.

Parse `tick_count` as an integer. Default: `1` if not provided (first invocation).

---

## Step 2: Read Status and Heartbeat

Read `backlog/.ralph-status.json` using the Read tool. If the file does not exist, stay silent — do NOT output anything. Schedule the next tick per Step 5 (including the incremented `tick_count`) and return.

Then run a single Bash call to get heartbeat mtime and current time:

```bash
stat -f %m backlog/.ralph-heartbeat 2>/dev/null || stat -c %Y backlog/.ralph-heartbeat 2>/dev/null; echo "---"; date +%s
```

Parse:
- `heartbeat_mtime`: first section (epoch, or empty if missing)
- `now`: second section (epoch)

Extract from the JSON (using grep/pattern matching, no jq):
- `state` — `"running"`, `"completed"`, or `"failed"`
- `pid`
- `iteration`
- `current_task`
- `iteration_started_at` — ISO 8601 timestamp
- `timeout_sec` — integer seconds
- `errors` — array of `{"iteration": N, "at": "<ISO>", "message": "<string>"}` objects
- `completed_at`, `exit_code`, `tasks_done`, `tasks_remaining`, `max_iterations`, `elapsed`

Convert `iteration_started_at` to epoch for comparison:
```bash
date -d "<iteration_started_at>" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "<iteration_started_at>" +%s 2>/dev/null
```

---

## Step 3: Apply Detection Rules (First Match Wins)

Apply these rules in order. The first rule that matches determines the output. Only one event is emitted per tick.

### Rule (e): Finished

**Condition:** `state` is `"completed"` or `"failed"`

**Timestamp conversion:** Before displaying `completed_at`, convert it from UTC to Europe/Moscow time using this portable Bash snippet:

```bash
utc_iso="<completed_at value>"
moscow_time=$(TZ=Europe/Moscow date -d "$utc_iso" "+%Y-%m-%d %H:%M:%S MSK" 2>/dev/null || TZ=Europe/Moscow date -j -f "%Y-%m-%dT%H:%M:%SZ" "$utc_iso" "+%Y-%m-%d %H:%M:%S MSK" 2>/dev/null)
```

**Output:** Full status block (same format as `/ralph-status`):

```
Ralph: finished (state=<state>, exit_code=<exit_code>)
========================================
State:        <state>
Progress:     iteration <iteration> of <max_iterations>
Elapsed:      <elapsed formatted>
Tasks done:   <tasks_done list or "none">
Remaining:    <tasks_remaining> tasks
Exit code:    <exit_code>
Completed at: <moscow_time converted from completed_at>
========================================
```

If `errors` is non-empty, append:
```
Errors:
  - [iteration <N>] <message>
```

**Terminal:** YES — do NOT schedule the next tick.

---

### Rule (f): Crashed

**Condition:** `state == "running"` AND `heartbeat_mtime` exists AND `(now - heartbeat_mtime) > 15`

**Output:**
```
Ralph: heartbeat stale > <age>s — process likely crashed (PID <pid>)
```

**Terminal:** YES — do NOT schedule the next tick.

---

### Rule (g): Stuck

**Condition:** `state == "running"` AND `iteration_started_at` is set AND `(now - iteration_started_at_epoch)` is in the range `[2 * timeout_sec, 2 * timeout_sec + interval_sec]`

This fires once when the iteration has been running for 2x the configured timeout, within the detection window.

**Output:**
```
Ralph: <current_task> stuck — iteration <iteration> running > <duration formatted> (2x the <timeout_sec/60>m timeout)
```

**Terminal:** NO — schedule the next tick.

---

### Rule (d): Failed Iteration

**Condition:** `state == "running"` AND any entry in `errors[]` has `at` timestamp within `[now - interval_sec, now]`

For each matching error, output one line:
```
Ralph: <current_task> — iteration <error.iteration> failed (<error.message>). Continuing.
```

**Terminal:** NO — schedule the next tick.

---

### No Match

Stay silent — output nothing. Schedule the next tick.

---

## Step 4: Safety Cap

If `tick_count` (parsed in Step 1) is >= 24, treat it as terminal regardless of state.

The tick count is self-tracked: each invocation receives `tick_count=N` via the `ScheduleWakeup` prompt, and increments it when scheduling the next tick (see Step 5). The first invocation defaults to `tick_count=1`.

If at the safety cap, output:
```
Ralph: watch safety cap reached (24 ticks). Use /ralph-status for manual checks.
```

Do NOT schedule the next tick.

---

## Step 5: Schedule Next Tick (if not terminal)

If no terminal flag was set and the safety cap has not been reached, call `ScheduleWakeup` with:
- `delaySeconds`: `interval_sec`
- `reason`: `"ralph-status-watch: polling Ralph (iteration <iteration>, state=<state>)"`
- `prompt`: `/ralph-status-watch interval=<original interval arg> tick_count=<tick_count + 1>`

The `tick_count` is incremented by 1 each tick, enabling the safety cap (Step 4) to terminate the loop after 24 ticks. The skill controls its own pacing via `ScheduleWakeup`, with the first tick scheduled by `ralph-run`.
