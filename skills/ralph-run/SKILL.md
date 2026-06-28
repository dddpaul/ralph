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
| model | claude-opus-4-8 | --model |
| effort | max | --effort |
| timeout | 60 | --timeout |
| tasks | (none) | --tasks |
| devcontainer | true | --devcontainer |
| verbose | false | --verbose |
| watch | (none) | — |
| block_end_buffer_min | 0 | --block-end-buffer-min |
| max_iterations | 10 | (positional, last arg) |

Set `block_end_buffer_min` to N>0 to pause the run when the active 5h Anthropic usage block has <=N minutes remaining. 0 disables the check (default). Requires ccusage to be installed; preflight warns if missing.

The `watch` parameter enables automatic progress monitoring after launch. Accepted values:
- `true` — normalized to `5m`
- `false` — no monitoring (same as omitting)
- A duration: `<N>s`, `<N>m`, or `<N>h` (e.g. `5m`, `30s`, `1h`)

Validate against regex `^(true|false|[0-9]+(s|m|h))$`. Reject invalid values:
```
BLOCKED: watch must be true, false, or a duration like 5m, 30s, 1h.
```

> **Note: Some skill defaults intentionally differ from ralph.sh CLI defaults.**
> The skill targets interactive sessions where a user launches Ralph from Claude Code,
> so it optimizes for thoroughness and isolation over speed:
> - **timeout** (skill: `60`, CLI: `15`) — max-effort iterations take longer; 15 minutes would time out most complex tasks.
> - **devcontainer** (skill: `true`, CLI: `false`) — interactive users expect sandboxed runs by default; the CLI leaves this opt-in for scripted/CI use.
>
> The `model` and `effort` defaults match the orchestrator's own defaults (`claude-opus-4-8` and `max`); the skill pins them explicitly so the launch command logs them and per-invocation overrides remain easy.

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

`ralph.sh` is the thin project shim that execs the canonical Python orchestrator (`~/.claude/skills/ralph-run/scripts/ralph_orchestrator.py`). Check in order:
1. `./ralph.sh`
2. `scripts/ralph/ralph.sh`

If none exists, report error and stop:
```
Error: ralph.sh not found. Checked ./ralph.sh and scripts/ralph/ralph.sh. Run /ralph-init to bootstrap the project shim.
```

---

## Step 3: Validate Preconditions

Run the preflight check (the `ralph.preflight` module in the `scripts/` directory next to this SKILL.md — i.e. `~/.claude/skills/ralph-run/scripts`) with the ralph path from Step 2 and the devcontainer flag from Step 1. Set `PYTHONPATH` to that scripts directory so `python -m ralph.preflight` resolves the package:

```bash
PYTHONPATH=<absolute-path-to-scripts-dir> uv run --no-project python -m ralph.preflight "$RALPH_PATH" <devcontainer:true|false> [--verbose] [--tasks <ids>] [--block-end-buffer-min <N>]
```

When `verbose=true`, append `--verbose` to the preflight command. This prints one `check <name>: <result>` line per check before the final OK/ERROR line.

When `tasks` is set, append `--tasks <ids>` to the preflight command.

When `block_end_buffer_min > 0`, append `--block-end-buffer-min <N>` to the preflight command.

If the output starts with `OK`, parse `RALPH_PATH` from the output (format: `OK RALPH_PATH=<path>`) and proceed to Step 4.

If the output starts with `ERROR:`, report the message verbatim to the user and stop.

---

## Step 4: Launch

Build the command from parsed arguments:

```bash
RALPH_CMD="<path-to-ralph.sh> --tool <tool> --model <model> --effort <effort> --timeout <timeout> <max_iterations>"
```

Add `--devcontainer` flag only if devcontainer=true.

When `tasks` is set, append `--tasks <ids>` to the command.

When `block_end_buffer_min > 0`, append `--block-end-buffer-min <N>` to the command.

Launch fully detached, capturing early output to a launch log. **You MUST set `dangerouslyDisableSandbox: true`** on this Bash tool call — the orchestrator needs full OS access (mktemp, /dev/fd, tee, docker) which the sandbox blocks.

```bash
LAUNCH_LOG='backlog/.ralph-launch.log'
nohup $RALPH_CMD > "$LAUNCH_LOG" 2>&1 & disown
RALPH_PID=$!
```

Wait for the heartbeat file to appear using the `ralph.wait_heartbeat` module (in the `scripts/` directory next to this SKILL.md). Set `PYTHONPATH` to that scripts directory as in Step 3:

```bash
PYTHONPATH=<absolute-path-to-scripts-dir> uv run --no-project python -m ralph.wait_heartbeat
```

It polls 10×1s for a fresh heartbeat (age < 15s). On success it prints `OK heartbeat age=...`, removes the launch log, and exits 0. On failure it prints `FAIL` with tails of both logs and exits 1.

Relay the command's stdout verbatim. Use the exit code: 0 → proceed to Step 5 success report; 1 → proceed to Step 5 failure report; 2 → invocation error (e.g. not run from project root).

---

## Step 5: Report

On success:

**If `watch` is empty (not set or `false`):** output one line plus a hint:

```
Ralph launched (PID <pid>, tool=<tool>, model=<model>, effort=<effort>, timeout=<timeout>m, max=<max_iterations>, devcontainer=<true|false>). /ralph-status to monitor, /ralph-stop to halt.

Hint: pass watch=5m to /ralph-run for automatic progress alerts.
```

**If `watch` is set (e.g. `5m`):** output the launch line AND schedule the first watch tick directly via `ScheduleWakeup`:

```
Ralph launched (PID <pid>, tool=<tool>, model=<model>, effort=<effort>, timeout=<timeout>m, max=<max_iterations>, devcontainer=<true|false>). Watching every <watch>.
```

Convert the `watch` duration to seconds using the same regex parser from Step 1 (e.g. `2m` → 120, `5m` → 300, `1h` → 3600).

Then call `ScheduleWakeup` with:
- `delaySeconds`: the parsed interval in seconds
- `reason`: `"ralph-status-watch first tick (interval=<watch>)"`
- `prompt`: `/ralph-status-watch interval=<watch>`

Do NOT invoke `/loop`. Subsequent ticks are self-paced by the watch skill via its own `ScheduleWakeup` chain (see ralph-status-watch SKILL.md Step 5).

On failure (process died immediately), output diagnostics from both logs:

```
Error: Ralph process exited immediately.

--- Last 20 lines of launch output (backlog/.ralph-launch.log) ---
<tail -20 backlog/.ralph-launch.log>

--- Last 20 lines of run log (backlog/.ralph-run.log, if exists) ---
<tail -20 backlog/.ralph-run.log, or 'not created' if file does not exist>

For full output, inspect both files.
```
