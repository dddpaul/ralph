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
3. `~/.claude/skills/ralph-run/scripts/ralph.sh`

If none exists, report error and stop:
```
Error: ralph.sh not found. Checked ./ralph.sh, scripts/ralph/ralph.sh, and ~/.claude/skills/ralph-run/scripts/ralph.sh
```

---

## Step 3: Validate Preconditions

Run the preflight script with the ralph path from Step 2 and the devcontainer flag from Step 1:

```bash
bash skills/ralph-run/scripts/preflight.sh "$RALPH_PATH" <devcontainer:true|false>
```

If the output starts with `OK`, parse `RALPH_PATH` from the output (format: `OK RALPH_PATH=<path>`) and proceed to Step 4.

If the output starts with `ERROR:`, report the message verbatim to the user and stop.

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

Wait for the heartbeat file to appear (up to 10 seconds), then verify freshness:

Wait up to 10 seconds for the heartbeat file to appear, then check freshness using `stat`:

```bash
stat -f %m backlog/.ralph-heartbeat 2>/dev/null || stat -c %Y backlog/.ralph-heartbeat 2>/dev/null
```

Compare the returned epoch with `date +%s`. If age < 15s, launch succeeded. If no heartbeat after 10s, launch failed.

On successful launch, remove the launch log (it only has diagnostic value on failure):

```bash
rm -f "$LAUNCH_LOG"
```

---

## Step 5: Report

On success, output exactly one line:

```
Ralph launched (PID <pid>, tool=<tool>, effort=<effort>, timeout=<timeout>m, max=<max_iterations>, devcontainer=<true|false>). /ralph-status to monitor, /ralph-stop to halt.
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
