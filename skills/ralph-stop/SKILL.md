---
name: ralph-stop
description: "Stop a running Ralph autonomous agent. Sends SIGTERM for graceful shutdown, falls back to SIGKILL after 10s. Triggers on: stop ralph, kill ralph, ralph stop."
---

# Ralph Stop

Gracefully stop a running Ralph autonomous agent.

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

Show current iteration and task info, then ask for confirmation:

```
Stop Ralph (PID <pid>) at iteration <iteration> of <max_iterations>, current task: <current_task>? [y/N]
```

If the user does not confirm, output `Cancelled.` and stop without action.

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
