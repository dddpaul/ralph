---
name: ralph-status
description: "Check Ralph autonomous agent progress. Reads status file and backlog to show concise summary. Triggers on: ralph status, check ralph, ralph progress, how is ralph doing."
---

# Ralph Status

Show a concise progress summary of a Ralph autonomous agent run.

---

## Step 1: Read Status File and Gather Data

Read `backlog/.ralph-status.json` using the Read tool. If the file does not exist, output the following and stop:

```
Ralph has not been run yet (no status file found).
Run /ralph-run to start Ralph.
```

Extract fields using grep from the file content (no jq/python dependency):
- `pid`, `started_at`, `state`, `iteration`, `max_iterations`, `tool`
- `tasks_done`, `tasks_remaining`, `current_task`
- `last_iteration_duration`, `elapsed`, `errors`
- `completed_at`, `exit_code`

Then run a **single** Bash call to get heartbeat mtime, current time, and backlog snapshot:

```bash
stat -f %m backlog/.ralph-heartbeat 2>/dev/null || stat -c %Y backlog/.ralph-heartbeat 2>/dev/null; echo "---"; date +%s; echo "---"; backlog task list --plain 2>/dev/null
```

Parse the output by splitting on `---`:
- First section: heartbeat mtime (epoch seconds, or empty if missing)
- Second section: current epoch time
- Third section: backlog task list

This gives you everything in **2 tool calls** (1 Read + 1 Bash).

---

## Step 2: Determine Liveness

If `state` is `"running"`, compute heartbeat age: `current_time - heartbeat_mtime`.

- If age < 15 seconds: process is **alive**, display state as `running`.
- If heartbeat is stale or missing: re-read `backlog/.ralph-status.json`. If it now shows `"completed"` or `"failed"`, use that state. Only show "crashed" if still `"running"`:
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

For running state, calculate elapsed as `current_time - started_at` (not the stale elapsed field from the file).
For completed/failed state, use the elapsed field from the file.

Format as:
- Under 60s: `<N>s`
- 60s and over: `<M>m <S>s`
- 3600s and over: `<H>h <M>m`

---

## Step 4: Show Errors

Each entry in the `errors` array is a structured object: `{"iteration": <int>, "at": "<ISO timestamp>", "message": "<string>"}`.

If the `errors` array is non-empty, output:

```
Errors:
  - [iteration <iteration>] <message>
  - [iteration <iteration>] <message>
```

Extract `iteration` and `message` from each object using grep/pattern matching on the JSON. The `at` field is available but not displayed in the summary (used by ralph-status-watch for time-based detection).

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

## Step 6: Backlog Summary

From the backlog task list output (already retrieved in Step 1), output a one-line count:

```
Backlog: <done> done, <in-progress> in progress, <to-do> to do
```

Count by status section headers (`Done:`, `In Progress:`, `To Do:`) and the number of task lines under each.
