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

> **Note: These defaults intentionally differ from ralph.sh CLI defaults.**
> The skill targets interactive sessions where a user launches Ralph from Claude Code,
> so it optimizes for thoroughness and isolation over speed:
> - **effort** (skill: `max`, CLI: `medium`) — interactive launches are typically fewer iterations on harder tasks; max effort avoids shallow results.
> - **timeout** (skill: `60`, CLI: `15`) — max-effort iterations take longer; 15 minutes would time out most complex tasks.
> - **devcontainer** (skill: `true`, CLI: `false`) — interactive users expect sandboxed runs by default; the CLI leaves this opt-in for scripted/CI use.

**Example invocations:**
- `/ralph-run` — all defaults
- `/ralph-run tool=opencode timeout=30 max_iterations=5`
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

Read `backlog/.ralph-status.json` if it exists. Extract the `pid` field using grep:

```bash
PID=$(grep -o '"pid":[0-9]*' backlog/.ralph-status.json | grep -o '[0-9]*')
```

Check if that process is still alive:

```bash
kill -0 $PID 2>/dev/null
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

### 3.4 ralph.sh integrity

Check that the script is executable:

```bash
if [[ ! -x "$RALPH_PATH" ]]; then
  echo 'Error: ralph.sh is not executable. Run: chmod +x ./ralph.sh'
  exit 1
fi
```

Check that the script has valid bash syntax:

```bash
if ! bash -n "$RALPH_PATH" 2>/tmp/ralph-syntax-err; then
  echo 'Error: ralph.sh has syntax errors:'
  cat /tmp/ralph-syntax-err
  exit 1
fi
```

If either check fails, report the specific check that failed with its error output and stop.

---

## Step 4: Launch

Build the command from parsed arguments:

```bash
RALPH_CMD="<path-to-ralph.sh> --tool <tool> --effort <effort> --timeout <timeout> <max_iterations>"
```

Add `--devcontainer` flag only if devcontainer=true.

Launch fully detached, capturing early output to a launch log. **You MUST set `dangerouslyDisableSandbox: true`** on this Bash tool call — ralph.sh needs full OS access (mktemp, /dev/fd, tee, docker) which the sandbox blocks.

```bash
LAUNCH_LOG='backlog/.ralph-launch.log'
nohup $RALPH_CMD > "$LAUNCH_LOG" 2>&1 & disown
RALPH_PID=$!
```

Wait briefly and verify the process started:

```bash
sleep 1
kill -0 $RALPH_PID 2>/dev/null
```

On successful launch, remove the launch log (it only has diagnostic value on failure):

```bash
rm -f "$LAUNCH_LOG"
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

On failure (process died immediately), output diagnostics from both logs:

```
Error: Ralph process exited immediately.

--- Last 20 lines of launch output (backlog/.ralph-launch.log) ---
<tail -20 backlog/.ralph-launch.log>

--- Last 20 lines of run log (backlog/.ralph-run.log, if exists) ---
<tail -20 backlog/.ralph-run.log, or 'not created' if file does not exist>

For full output, inspect both files.
```
