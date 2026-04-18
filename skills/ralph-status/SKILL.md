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

Parse the JSON and extract all fields:
- `pid`, `started_at`, `state`, `iteration`, `max_iterations`, `tool`
- `tasks_done`, `tasks_remaining`, `current_task`
- `last_iteration_duration`, `elapsed`, `errors`
- `completed_at`, `exit_code`

---

## Step 2: Verify PID (Running State Only)

If `state` is `"running"`, check whether the process is actually alive:

```bash
kill -0 <pid> 2>/dev/null
```

- If the process is **not alive**, override the displayed state:
  ```
  State: crashed (PID <pid> not found)
  ```
- If the process **is alive**, display state as `running`.

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
