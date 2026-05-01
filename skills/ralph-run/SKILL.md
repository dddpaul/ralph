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
| tasks | (none) | --tasks |
| devcontainer | true | --devcontainer |
| verbose | false | --verbose |
| watch | (none) | — |
| max_iterations | 10 | (positional, last arg) |

The `watch` parameter enables automatic progress monitoring after launch. Accepted values:
- `true` — normalized to `5m`
- `false` — no monitoring (same as omitting)
- A duration: `<N>s`, `<N>m`, or `<N>h` (e.g. `5m`, `30s`, `1h`)

Validate against regex `^(true|false|[0-9]+(s|m|h))$`. Reject invalid values:
```
BLOCKED: watch must be true, false, or a duration like 5m, 30s, 1h.
```

> **Note: These defaults intentionally differ from ralph.sh CLI defaults.**
> The skill targets interactive sessions where a user launches Ralph from Claude Code,
> so it optimizes for thoroughness and isolation over speed:
> - **effort** (skill: `max`, CLI: `medium`) — interactive launches are typically fewer iterations on harder tasks; max effort avoids shallow results.
> - **timeout** (skill: `60`, CLI: `15`) — max-effort iterations take longer; 15 minutes would time out most complex tasks.
> - **devcontainer** (skill: `true`, CLI: `false`) — interactive users expect sandboxed runs by default; the CLI leaves this opt-in for scripted/CI use.

The `tasks` parameter accepts comma-separated numeric task IDs only (e.g. `62,64,65`). Reject `TASK-` prefix or non-numeric values. Mutually exclusive with `--prompt-file`.

**Example invocations:**
- `/ralph-run` — all defaults
- `/ralph-run tool=opencode timeout=30 max_iterations=5`
- `/ralph-run devcontainer=false effort=high`
- `/ralph-run tasks=62` — only TASK-62
- `/ralph-run tasks=62,64,65 max_iterations=3`
- `/ralph-run watch=5m` — launch with automatic 5-minute progress alerts
- `/ralph-run tasks=70 watch=2m max_iterations=3` — watch with custom interval

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

Run the preflight script (`scripts/preflight.sh` in the directory next to this SKILL.md) with the ralph path from Step 2 and the devcontainer flag from Step 1:

```bash
bash <absolute-path-to-scripts/preflight.sh> "$RALPH_PATH" <devcontainer:true|false> [--verbose] [--tasks <ids>]
```

When `verbose=true`, append `--verbose` to the preflight command. This prints one `check <name>: <result>` line per check before the final OK/ERROR line.

When `tasks` is set, append `--tasks <ids>` to the preflight command.

If the output starts with `OK`, parse `RALPH_PATH` from the output (format: `OK RALPH_PATH=<path>`) and proceed to Step 4.

If the output starts with `ERROR:`, report the message verbatim to the user and stop.

---

## Step 4: Launch

Build the command from parsed arguments:

```bash
RALPH_CMD="<path-to-ralph.sh> --tool <tool> --effort <effort> --timeout <timeout> <max_iterations>"
```

Add `--devcontainer` flag only if devcontainer=true.

When `tasks` is set, append `--tasks <ids>` to the command.

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

On success:

**If `watch` is empty (not set or `false`):** output one line plus a hint:

```
Ralph launched (PID <pid>, tool=<tool>, effort=<effort>, timeout=<timeout>m, max=<max_iterations>, devcontainer=<true|false>). /ralph-status to monitor, /ralph-stop to halt.

Hint: pass watch=5m to /ralph-run for automatic progress alerts.
```

**If `watch` is set (e.g. `5m`):** output the launch line AND immediately invoke the `/loop` skill to start a dynamic-mode loop for automatic monitoring:

```
Ralph launched (PID <pid>, tool=<tool>, effort=<effort>, timeout=<timeout>m, max=<max_iterations>, devcontainer=<true|false>). Watching every <watch>.
```

Then invoke: `/loop /ralph-status-watch interval=<watch>`

This starts a dynamic-mode loop (no positional interval to `/loop`) where the watch skill self-paces via `ScheduleWakeup` at the configured interval. Dynamic mode allows the loop to terminate naturally when the watch skill detects a terminal event and omits the `ScheduleWakeup` call.

On failure (process died immediately), output diagnostics from both logs:

```
Error: Ralph process exited immediately.

--- Last 20 lines of launch output (backlog/.ralph-launch.log) ---
<tail -20 backlog/.ralph-launch.log>

--- Last 20 lines of run log (backlog/.ralph-run.log, if exists) ---
<tail -20 backlog/.ralph-run.log, or 'not created' if file does not exist>

For full output, inspect both files.
```
