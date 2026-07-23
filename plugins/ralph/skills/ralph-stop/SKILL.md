---
name: ralph-stop
description: "Stop a running Ralph autonomous agent. Sends SIGTERM for graceful shutdown, falls back to SIGKILL after 10s. Triggers on: stop ralph, kill ralph, ralph stop."
---

# Ralph Stop

Gracefully stop a running Ralph autonomous agent.

---

## Behavior: graceful drain, not mid-iteration kill

`ralph-stop` signals the **host-side orchestrator** (`ralph.sh` — the PID in the status file). It does NOT reach the AI agent (`claude -p` / `opencode`) running the current iteration: for `--devcontainer` runs that agent is a Docker-isolated process the host's `pkill -P <pid>` / `kill` cannot see.

This is intentional. The effect is a **graceful drain**:

- SIGTERM to the orchestrator stops it from spawning the *next* iteration.
- The in-flight iteration's agent keeps running to completion and merges its task cleanly.
- The loop then halts because no orchestrator remains to start the following task.

So "stop" lands on a **clean task boundary**: the current task finishes and merges (no half-written diff), then Ralph stops. Net semantics: *"stop after task N"* drains to *"after N plus whatever task is already in flight."*

Do NOT "fix" this by force-killing the in-container agent (e.g. `devcontainer exec ... pkill claude`). Killing `claude -p` mid-iteration leaves a partial, uncommitted diff on the task branch that needs `git reset` + manual cleanup — the opposite of a graceful stop.

Note: ralph-stop is a plugin skill, not a bootstrap-seeded template, so there is NO R11 template-parity pair to also edit — single file change. The installed plugin-cache copy updates on next plugin reinstall; only the repo source is edited here.

---

## Step 1: Read Status File

Read `backlog/.ralph-status.json`. If the file does not exist, output the following and stop:

```
No Ralph has been run yet (no status file found).
```

Extract fields using grep (no jq/python dependency):

```bash
STATUS_FILE="backlog/.ralph-status.json"
PID=$(grep -o '"pid":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
STATE=$(grep -o '"state":"[^"]*"' "$STATUS_FILE" | grep -o '"[^"]*"$' | tr -d '"')
ITERATION=$(grep -o '"iteration":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
MAX_ITERATIONS=$(grep -o '"max_iterations":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
CURRENT_TASK=$(grep -o '"current_task":"[^"]*"' "$STATUS_FILE" | grep -o '"[^"]*"$' | tr -d '"')
```

---

## Step 2: Verify State

If `state` is not `"running"`, output the following and stop:

```
Ralph is not running (state: <state>). Nothing to stop.
```

---

## Step 3: Verify PID Alive

Check whether the process is actually alive:

```bash
kill -0 <pid> 2>/dev/null
```

If the process is **not alive**, output the following and stop:

```
Ralph PID <pid> not found (probably crashed). Status file is stale.
```

---

## Step 4: Confirm with User

Output a one-line status header, then end the response with an `<options>` block on its own lines:

```
Stop Ralph (PID <pid>) at iteration <iteration> of <max_iterations>, current task: <current_task>?
```

```
<options>
<option>Stop Ralph</option>
<option>Cancel</option>
</options>
```

The `<options>` block must be at the very end of the response, not nested inside other text or a codeblock.

On the next turn, if the user chose **Stop Ralph**, proceed to Step 5. For any other reply (including **Cancel**), output `Cancelled.` and stop without sending any signals.

---

## Step 5: Graceful Shutdown

First, kill all descendant processes (child tool processes may be in separate process groups):

```bash
pkill -TERM -P <pid> 2>/dev/null
```

Then send SIGTERM to ralph.sh itself:

```bash
kill -TERM <pid>
```

Poll for exit, up to 10 attempts at 1-second intervals:

```bash
for i in $(seq 1 10); do
  if ! kill -0 <pid> 2>/dev/null; then
    break
  fi
  sleep 1
done
```

---

## Step 6: Force Kill if Needed

If the process is still alive after 10 seconds, force-kill the entire process tree:

```bash
pkill -KILL -P <pid> 2>/dev/null
kill -KILL <pid> 2>/dev/null
sleep 1
```

Verify the process is dead. If it is still alive, report:

```
Warning: Ralph PID <pid> could not be killed. Manual intervention required.
```

---

## Step 7: Report

Re-read `backlog/.ralph-status.json` to get the final state after trap handlers have run. Output:

```
Ralph stopped (PID <pid>). Final state: <state>.
```
