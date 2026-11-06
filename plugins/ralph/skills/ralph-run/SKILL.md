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
| model | claude-opus-5-5 | --model |
| effort | medium | --effort |
| timeout | 60 | --timeout |
| tasks | (none) | --tasks |
| devcontainer | true | --devcontainer |
| rebuild | false | --rebuild |
| verbose | false | --verbose |
| push | true | --no-push (when false) |
| watch | (none) | — |
| block_end_buffer_min | 0 | --block-end-buffer-min |
| max_iterations | 10 | (positional, last arg) |

Set `block_end_buffer_min` to N>0 to pause the run when the active 5h Anthropic usage block has <=N minutes remaining. 0 disables the check (default). Requires ccusage to be installed; preflight warns if missing.

**A run pushes `master` to `origin`.** With `push=true` (the default), the orchestrator runs `git push origin master` once at the end of the run whenever `master` moved during it. `push.followTags` carries the version tags along. The push also happens after a `/ralph-stop` or a failed run, because it runs after the loop's cleanup and not inside it. The git `pre-push` hook still runs on that push and can reject it. Set `push=false` to skip the push for this run: Step 4 passes `--no-push`, and the merged work stays on the local `master` only. Accepted values are `true` and `false`; reject anything else:
```
BLOCKED: push must be true or false.
```

Set `rebuild=true` to force a **fresh** container instead of reusing the existing one — the orchestrator then runs `devcontainer up ... --remove-existing-container`. Needed only after editing `.devcontainer/devcontainer.json`, because mounts and other container config apply at container **creation**: a reused container silently ignores them. Without `rebuild=true`, the orchestrator refuses to reuse a container created before the last change to `.devcontainer/devcontainer.json` or `.devcontainer/Dockerfile`: the launch fails the heartbeat check and the launch log shows a `STALE DEVCONTAINER` banner with both timestamps — relaunch with `rebuild=true`. Off by default (a rebuild is expensive), and a no-op unless `devcontainer=true`. It does **not** refresh the image: cached layers are reused wherever their inputs are unchanged, so a floating version tag would stay frozen. The Claude Code version is therefore pinned as `CLAUDE_CODE_VERSION` in `devcontainer.json` (bumping it invalidates the npm layer); to force a fresh image regardless, run `devcontainer build --workspace-folder . --no-cache` by hand.

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
> - **timeout** (skill: `60`, CLI: `15`) — interactive runs target whole backlog tasks, so 15 minutes would time out most complex tasks.
> - **devcontainer** (skill: `true`, CLI: `false`) — interactive users expect sandboxed runs by default; the CLI leaves this opt-in for scripted/CI use.
>
> The `model` and `effort` defaults match the orchestrator's own defaults (`claude-opus-5-5` and `medium`); the skill pins them explicitly so the launch command logs them and per-invocation overrides remain easy.

The `tasks` parameter accepts comma-separated numeric task IDs only (e.g. `62,64,65`). Reject `TASK-` prefix or non-numeric values. Mutually exclusive with `--prompt-file`.

**Example invocations:**
- `/ralph-run` — all defaults
- `/ralph-run tool=opencode timeout=30 max_iterations=5`
- `/ralph-run devcontainer=false effort=high`
- `/ralph-run push=false` — run without pushing `master` to `origin` at the end
- `/ralph-run rebuild=true` — recreate the container so devcontainer.json mount changes take effect
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

Run the preflight check via its bash launcher shim (`preflight.sh` in the `scripts/` directory next to this SKILL.md — i.e. `${CLAUDE_PLUGIN_ROOT}/skills/ralph-run/scripts`) with the ralph path from Step 2 and the devcontainer flag from Step 1. The shim resolves its own directory as `PYTHONPATH` and execs `python -m ralph.preflight`. The harness renders `${CLAUDE_PLUGIN_ROOT}` to the installed plugin directory; preflight is read-only, so sandbox auto-allow covers it and no allow-rule is needed (measured on Claude Code 2.1.280; a host on an older build that prompts here should upgrade Claude Code — see ralph-init Step 3.7a):

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-run/scripts/preflight.sh "$RALPH_PATH" <devcontainer:true|false> [--verbose] [--tasks <ids>] [--block-end-buffer-min <N>]
```

When `verbose=true`, append `--verbose` to the preflight command. This prints one `check <name>: <result>` line per check before the final OK/ERROR line.

When `tasks` is set, append `--tasks <ids>` to the preflight command.

When `block_end_buffer_min > 0`, append `--block-end-buffer-min <N>` to the preflight command.

If the output has a line starting with `OK`, parse `RALPH_PATH` from it (format: `OK RALPH_PATH=<path>`) and proceed to Step 4 — `WARNING:` lines may precede it.

If the output has a line starting with `ERROR:`, report the message verbatim to the user and stop.

Preflight also prints one `WARNING: ralph-init managed file behind the installed plugin — <path>: outdated|missing` line on stderr per ralph-init managed file (`ralph.sh`, `CLAUDE.md`'s generic section, git hooks, `.claude/hooks/`, …) whose content differs from the installed plugin's template, from ralph-init's `managed-file-drift.sh`. When the check itself cannot run it prints `WARNING: could not check ralph-init managed files — <reason>` instead. These never abort: relay them to the user once, recommend running the ralph-init upgrade after this run (or, for the second form, report the reason), and proceed to Step 4.

With `devcontainer=true`, preflight also reads the user settings file (`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json`) and prints one `WARNING: user hook not reachable in the devcontainer — <Event>: <command> (guard the hook command with DEVCONTAINER, see ralph-init)` line on stderr per hook command whose executable is a path outside the user Claude config dir (an absolute path, or `$HOME/...` / `${HOME}/...` / `~/...`). The container shares only `~/.claude`, so such a hook fails there with "not found" on every event it is registered for. Bare command names, paths under the config dir, and commands guarded with `[ "${DEVCONTAINER:-}" = true ] || ...` are not reported; a missing or unparsable settings file reports nothing. This warning never aborts: relay it to the user once, point at the user-hook contract in ralph-init's devcontainer notes, and proceed to Step 4. Ralph never edits the user's hooks.

Preflight also compares the user settings file (`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json`) with the plugin's `user-settings.json` fragment: the common `Bash(...)` allow rules, `ScheduleWakeup`, `attribution` with an empty commit and PR trailer, and `sandbox` with `enabled` and `autoAllowBashIfSandboxed`. A plugin cannot ship allow rules itself, so these belong in user settings. When entries are missing, it prints one `WARNING: user settings miss <N> ralph entries — <entry>; <entry>; … (add them to <settings> from <fragment>)` line on stderr; an allow rule reads as `permissions.allow: <rule>` and any other value as `<key.path>=<json>`. A value that differs from the fragment is the user's choice and is not reported. An unparsable settings file prints `WARNING: could not check user settings for ralph entries — <reason>` instead. Preflight changes no file. This warning never aborts: relay it to the user once and proceed to Step 4. The owner adds the entries by hand, or runs `bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-run/scripts/merge-user-settings.sh <settings.json>`, which configuration management also runs on a second host from the installed plugin's `installPath`. The merge appends missing allow rules and keys, keeps every other key and value, and reports each differing value on stderr (`differs: <key.path>: kept <value>, fragment has <value>`) without overwriting it.

In a project whose `.claude/ralph.json` sets `"pluginHooks": true`, the plugin owns the six Claude guards and the common allow rules, so the drift check no longer compares `.claude/settings.json`, `.claude/settings.local.json` or the guard copies; a copy of a guard the marker does not list in `localGuards` reads `<path>: legacy copy` (rerun `migrate-plugin-hooks.sh tracked` to delete it). In a clone whose `git config ralph.pluginHooks` is true, the three git hooks are compared with the plugin shim instead of the legacy bodies.

Preflight also reports the project's migration to plugin hooks, as `WARNING: plugin hooks: <state>` lines on stderr: `not migrated` (no marker; the project runs its own guard copies), `partially migrated` (the marker is set but `.claude/settings.json` still runs legacy guard copies, or there is no marker but some guard copies are gone), `shims missing in this clone` (the marker is set but this clone's pre-commit, commit-msg or post-commit is not the plugin shim, or `ralph.pluginHooks` is not true), and, whenever the marker is set, `plugin guards are best effort` (a plugin guard hook that cannot start does not block the command; the git hooks still block on `ralph.pluginHooks`). Each line names the `migrate-plugin-hooks.sh` subcommand to run: `tracked` once per project on one host, then commit it; `clone` once per clone on every host, after `git pull` on the second one — it commits nothing. These never abort: relay them to the user once and proceed to Step 4.

A deliberate, reviewed difference can be accepted so it stops warning: list it in `<project>/.claude/managed-file-drift.accept`, one `<path> template=<sha256> project=<sha256>` line per path (blank lines and `#` comments allowed). Get the line from `bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-init/scripts/managed-file-drift.sh accept . <path>` and append it yourself — the subcommand only prints it, and exits 2 for a path that is unmanaged, missing or already current. Each hash covers exactly what the check compares (for `CLAUDE.md`, only the lines above `## Project-Specific`), so the warning returns as soon as either the template or the project file changes — notably after a plugin release that touches the template. A malformed line turns into the `could not check` warning naming the file and line number. A project that ignores `.claude/*` needs a `!.claude/managed-file-drift.accept` line in `.gitignore` to commit the file.

---

## Step 4: Launch

Build the command as a shell array (**not** a string — see the note below):

```bash
RALPH_CMD=(<path-to-ralph.sh> --tool <tool> --model <model> --effort <effort> --timeout <timeout> <max_iterations>)
```

Append conditional flags as array elements (never string concatenation):

- devcontainer=true → `RALPH_CMD+=(--devcontainer)`
- devcontainer=true **and** rebuild=true → `RALPH_CMD+=(--rebuild)` (skip it when devcontainer=false — the flag is a no-op there)
- `tasks` is set → `RALPH_CMD+=(--tasks <ids>)`
- `block_end_buffer_min > 0` → `RALPH_CMD+=(--block-end-buffer-min <N>)`
- push=false → `RALPH_CMD+=(--no-push)` (push=true adds nothing: the orchestrator pushes by default, see Step 1)

Launch fully detached, capturing early output to a launch log. **You MUST set `dangerouslyDisableSandbox: true`** on this Bash tool call — the orchestrator needs full OS access (mktemp, /dev/fd, tee, docker) which the sandbox blocks.

```bash
LAUNCH_LOG='backlog/.ralph-launch.log'
nohup "${RALPH_CMD[@]}" > "$LAUNCH_LOG" 2>&1 & disown
RALPH_PID=$!
```

> **Note — zsh word-splitting:** Build `RALPH_CMD` as an array and expand it with `"${RALPH_CMD[@]}"`; never store the command in a string and run it as unquoted `$RALPH_CMD`. Under zsh — the shell Claude Code's Bash tool uses — unquoted parameter expansion does **not** word-split, so `nohup $RALPH_CMD` hands the whole command to `nohup` as a single argv[0] and dies with `No such file or directory`. The array form passes `<path-to-ralph.sh>` as argv[0] and each flag as a separate argument identically under bash and zsh.

Wait for the heartbeat file to appear using the `wait-heartbeat.sh` launcher shim (in the `scripts/` directory next to this SKILL.md). Invoke it the same way as the Step 3 preflight — the shim sets its own `PYTHONPATH` and execs `python -m ralph.wait_heartbeat`, and the harness renders `${CLAUDE_PLUGIN_ROOT}` to the installed plugin directory:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-run/scripts/wait-heartbeat.sh && rm -f backlog/.ralph-launch.log
```

The shim itself is read-only. It polls 10×1s for a fresh heartbeat (age < 15s). On success it prints `OK heartbeat age=...` and exits 0; the trailing `rm -f` then removes the now-superfluous launch log. On failure it prints `FAIL` with tails of both logs and exits 1 — the `&&` short-circuits, so the launch log survives for the Step 5 failure report.

Relay the command's stdout verbatim. Use the exit code: 0 → proceed to Step 5 success report; 1 → proceed to Step 5 failure report; 2 → invocation error (e.g. not run from project root).

---

## Step 5: Report

On success:

**If `watch` is empty (not set or `false`):** output one line plus a hint:

```
Ralph launched (PID <pid>, tool=<tool>, model=<model>, effort=<effort>, timeout=<timeout>m, max=<max_iterations>, devcontainer=<true|false>, push=<true|false>). /ralph-status to monitor, /ralph-stop to halt.

Hint: pass watch=5m to /ralph-run for automatic progress alerts.
```

**If `watch` is set (e.g. `5m`):** output the launch line AND schedule the first watch tick directly via `ScheduleWakeup`:

```
Ralph launched (PID <pid>, tool=<tool>, model=<model>, effort=<effort>, timeout=<timeout>m, max=<max_iterations>, devcontainer=<true|false>, push=<true|false>). Watching every <watch>.
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
