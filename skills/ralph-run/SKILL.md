---
name: ralph-run
description: "Launch Ralph autonomous agent in the background from an interactive Claude Code session. Handles nohup/disown for full process detachment. Validates preconditions before launching. Triggers on: ralph run, start ralph, launch ralph, run ralph."
---

# Ralph Runner

Launch ralph.sh as a fully detached background process from an interactive Claude Code session.

---

## Step 1: Parse Arguments

The user may pass overrides as skill arguments. Parse them as space-separated key=value pairs.

**Defaults:**

| Parameter | Default | Flag |
|-----------|---------|------|
| tool | claude | --tool |
| effort | max | --effort |
| timeout | 60 | --timeout |
| devcontainer | true | --devcontainer |
| max_iterations | 10 | (positional, last arg) |

**Example invocations:**
- `/ralph-run` — all defaults
- `/ralph-run tool=amp timeout=30 max_iterations=5`
- `/ralph-run devcontainer=false effort=high`

---

## Step 2: Locate ralph.sh

Check in order:
1. `./ralph.sh`
2. `scripts/ralph/ralph.sh`

If neither exists, report error and stop:
```
Error: ralph.sh not found. Checked ./ralph.sh and scripts/ralph/ralph.sh
```

---

## Step 3: Validate Preconditions

### 3.1 To Do tasks exist

```bash
backlog task list -s "To Do" --plain 2>/dev/null
```

If no "To Do" tasks found, report and stop:
```
Error: No "To Do" tasks in backlog. Create tasks first (e.g. /ralph-backlog).
```

### 3.2 Ralph not already running

Read `backlog/.ralph-status.json` if it exists. Extract the `pid` field. Check if that process is still alive:

```bash
kill -0 <pid> 2>/dev/null
```

If the process is alive, report and stop:
```
Error: Ralph is already running (PID <pid>). Use /ralph-status to check progress, or kill <pid> to stop it.
```

If the status file doesn't exist or the PID is not alive, proceed.

### 3.3 devcontainer CLI (only when devcontainer=true)

```bash
command -v devcontainer
```

If missing and devcontainer=true, report and stop:
```
Error: devcontainer CLI not found but --devcontainer is enabled. Install it or run with devcontainer=false.
```

---

## Step 4: Launch

Build the command from parsed arguments:

```bash
RALPH_CMD="<path-to-ralph.sh> --tool <tool> --effort <effort> --timeout <timeout> <max_iterations>"
```

Add `--devcontainer` flag only if devcontainer=true.

Launch fully detached so Ralph survives the session ending:

```bash
nohup bash -c "$RALPH_CMD" > /dev/null 2>&1 & disown
RALPH_PID=$!
```

Wait briefly and verify the process started:

```bash
sleep 1
kill -0 $RALPH_PID 2>/dev/null
```

---

## Step 5: Report

On success, output:

```
Ralph launched successfully!

  PID: <pid>
  Tool: <tool>
  Effort: <effort>
  Timeout: <timeout> minutes
  Max iterations: <max_iterations>
  Devcontainer: <true/false>

Ralph is running in the background. Use /ralph-status to check progress.
To stop: kill <pid>
```

On failure (process died immediately), output:

```
Error: Ralph process exited immediately. Check backlog/.ralph-run.log for details.
```
