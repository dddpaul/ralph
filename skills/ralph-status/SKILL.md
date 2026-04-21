---
name: ralph-status
description: "Check Ralph autonomous agent progress. Reads status file and backlog to show concise summary. Triggers on: ralph status, check ralph, ralph progress, how is ralph doing."
---

# Ralph Status

Show a concise progress summary of a Ralph autonomous agent run.

---

## Step 1: Read Status File

Read `backlog/.ralph-status.json`. If the file does not exist, output the following and stop:

```
Ralph has not been run yet (no status file found).
Run /ralph-run to start Ralph.
```

Extract fields using grep (no jq/python dependency):

```bash
STATUS_FILE="backlog/.ralph-status.json"
PID=$(grep -o '"pid":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
STATE=$(grep -o '"state":"[^"]*"' "$STATUS_FILE" | grep -o '"[^"]*"$' | tr -d '"')
ITERATION=$(grep -o '"iteration":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
MAX_ITERATIONS=$(grep -o '"max_iterations":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
TOOL=$(grep -o '"tool":"[^"]*"' "$STATUS_FILE" | grep -o '"[^"]*"$' | tr -d '"')
STARTED_AT=$(grep -o '"started_at":"[^"]*"' "$STATUS_FILE" | grep -o '"[^"]*"$' | tr -d '"')
ELAPSED=$(grep -o '"elapsed":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
TASKS_REMAINING=$(grep -o '"tasks_remaining":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
CURRENT_TASK=$(grep -o '"current_task":"[^"]*"' "$STATUS_FILE" | grep -o '"[^"]*"$' | tr -d '"')
EXIT_CODE=$(grep -o '"exit_code":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
COMPLETED_AT=$(grep -o '"completed_at":"[^"]*"' "$STATUS_FILE" | grep -o '"[^"]*"$' | tr -d '"')
```

For array fields (`tasks_done`, `errors`), read the raw JSON arrays from the file content.

Extract all fields:
- `pid`, `started_at`, `state`, `iteration`, `max_iterations`, `tool`
- `tasks_done`, `tasks_remaining`, `current_task`
- `last_iteration_duration`, `elapsed`, `errors`
- `completed_at`, `exit_code`

---

## Step 2: Verify Liveness (Running State Only)

If `state` is `"running"`, check whether the process is actually alive using the heartbeat file. No special sandbox permissions are needed.

```bash
HEARTBEAT="backlog/.ralph-heartbeat"
MTIME=$(stat -f %m "$HEARTBEAT" 2>/dev/null || stat -c %Y "$HEARTBEAT" 2>/dev/null)
NOW=$(date +%s)
[[ $((NOW - MTIME)) -lt 15 ]]
```

- If the heartbeat file is **fresh** (modified within the last 15 seconds), display state as `running`.
- If the heartbeat file is **stale or missing**, re-read `backlog/.ralph-status.json` — ralph may have written a final status between your first read and the heartbeat check. If the re-read shows `"completed"` or `"failed"`, use that state (not "crashed"). Only show "crashed" if the state is still `"running"` after the re-read:
  ```
  State: crashed (heartbeat stale, PID <pid>)
  ```

Skip this check for `"completed"` and `"failed"` states.

---

## Step 3: Format Summary

Output a concise summary block:

```
Ralph Status
============
State:        <state> (or "crashed" per Step 2)
Tool:         <tool>
Progress:     iteration <iteration> of <max_iterations>
Elapsed:      <elapsed formatted as Xm Ys>
PID:          <pid>

Current task: <current_task or "none">
Done:         <comma-separated tasks_done list, or "none">
Remaining:    <tasks_remaining> tasks
```

If `state` is `"completed"` or `"failed"`, also show:

```
Exit code:    <exit_code>
Completed at: <completed_at>
```

### Formatting elapsed time

Convert the `elapsed` seconds value to human-readable format:
- Under 60s: `<N>s`
- 60s and over: `<M>m <S>s`
- 3600s and over: `<H>h <M>m`

---

## Step 4: Show Errors

If the `errors` array is non-empty, output:

```
Errors:
  - <error 1>
  - <error 2>
```

---

## Step 5: Log Tail (On Request)

Check if the user's skill arguments contain the word `log`, `logs`, `details`, or `verbose`.

If yes, and `backlog/.ralph-run.log` exists, show the last 20 lines:

```
Recent log output:
------------------
<last 20 lines of backlog/.ralph-run.log>
```

If the log file does not exist, output:

```
No log file found (backlog/.ralph-run.log).
```

If the user did not request details, add this hint at the end of the output:

```
Tip: /ralph-status details — to include recent log output
```

---

## Step 6: Current Backlog Snapshot

Run:

```bash
backlog task list --plain 2>/dev/null
```

Output a one-line count summary below the status block:

```
Backlog: <done> done, <in-progress> in progress, <to-do> to do
```

Count tasks by scanning the output for status markers: `✔` for done, `▶` for in progress, `○` for to do.
