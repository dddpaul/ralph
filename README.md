# Ralph

![Ralph](ralph.webp)

Ralph is an autonomous AI agent loop that runs AI coding tools ([Claude Code](https://docs.anthropic.com/en/docs/claude-code) or [opencode](https://opencode.ai)) repeatedly until all backlog tasks are complete. The loop itself is a Python orchestrator; each project keeps a thin `ralph.sh` shim that execs it via [uv](https://docs.astral.sh/uv/). Each iteration is a fresh instance with clean context. Memory persists via git history, backlog task notes, and CLAUDE.md/AGENTS.md files.

Based on [Geoffrey Huntley's Ralph pattern](https://ghuntley.com/ralph/) and [Ryan Carson's original Ralph implementation](https://x.com/ryancarson/status/2008548371712135632).

### How this fork differs from the original

The original Ralph uses a single `prd.json` file with `jq` parsing, a shared `progress.txt` for learnings, and one long-lived feature branch per run. This fork replaces all of that with the [Backlog.md CLI](https://github.com/MrLesk/Backlog.md) — each task is a separate file with built-in status, acceptance criteria, and notes. Tasks get per-task branches (`task-<id>-description`) merged to master individually, mandatory code review before every merge, and a `MODE: autonomous` prefix so the same CLAUDE.md works for both the Ralph loop and interactive development.

## Prerequisites

- One of the following AI coding tools installed and authenticated:
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`npm install -g @anthropic-ai/claude-code`) (default)
  - [opencode](https://opencode.ai) (`npm install -g @opencode/cli`)
- [uv](https://docs.astral.sh/uv/) with Python 3.14 — the Ralph loop runs a Python orchestrator (`ralph.sh` execs `ralph_orchestrator.py` via `uv run`), so both are required regardless of your project's own language
- [Backlog.md CLI](https://github.com/MrLesk/Backlog.md) installed
- A git repository for your project
- For running tests: [bats-core](https://github.com/bats-core/bats-core) (`npm install` or see [bats-core installation](https://github.com/bats-core/bats-core#installation)) for the bash tests; the Python orchestrator tests run under `uv run pytest`

## First-time setup

Ralph ships as a single Claude Code plugin (`ralph`) in the `dddpaul-ralph` marketplace, bundling every `ralph-*` skill plus the `task-reviewer` and `ralph-reviewer` agents. Install it once and they become available in every project:

```
/plugin marketplace add dddpaul/ralph
/plugin install ralph@dddpaul-ralph
```

**Updating:** re-run `/plugin marketplace add dddpaul/ralph` (or `/plugin update ralph@dddpaul-ralph`) to pull the latest version. `ralph-init` does not manage `~/.claude/` — the user owns that directory.

## Setup

### Option 1: Copy to your project

Copy the ralph files into your project:

```bash
# From your project root
mkdir -p scripts/ralph
cp /path/to/ralph/ralph.sh scripts/ralph/
cp /path/to/ralph/CLAUDE.md scripts/ralph/CLAUDE.md
chmod +x scripts/ralph/ralph.sh
```

### Option 2: Install skills globally

Make the skills available across all projects.

For Claude Code, install the plugin (same as [First-time setup](#first-time-setup)):
```
/plugin marketplace add dddpaul/ralph
/plugin install ralph@dddpaul-ralph
```

opencode has no plugin marketplace, so copy the skills manually from the plugin tree:
```bash
cp -r plugins/ralph/skills/ralph-* ~/.opencode/skills/
```

### Option 3: Run in DevContainer (sandboxed)

The repository includes a DevContainer with firewall restrictions for sandboxed autonomous agent execution. Network access is limited to approved domains only (GitHub, npm, Anthropic API, etc.).

**Runtime:** The default Dockerfile includes Go 1.25, but you can replace Stage 1 with any language runtime (Python, Ruby, Java, etc.) by modifying `.devcontainer/Dockerfile`.

To run Ralph in the devcontainer:

```bash
./ralph.sh --devcontainer [max_iterations]
```

This starts the container automatically and executes Ralph inside the isolated environment. The firewall (`init-firewall.sh`) restricts outbound network access using iptables and validates restrictions on startup.

## Workflow

### 1. Brainstorm (recommended)

For new projects or substantial features, start with the [brainstorm skill](https://github.com/umputun/cc-thingz/tree/master/plugins/brainstorm) to converge on architecture, integration boundaries, and scope before writing anything to disk:

```
/brainstorm <your feature description>
```

The dialogue produces a clear architectural decision and a list of components/flows that feed into Step 2. After the dialogue, save conclusions to `design/<name>-brainstorm.md` (the project `brainstorm-rules.md` will propose this). Skip this step for trivial changes where the design is obvious.

The `design/` folder is the canonical location for intent documents — brainstorms, PRDs, and reviews all live here.

When saving the brainstorm, include the mandatory **"Distilled for ralph-task"** block (Direction, Locked decisions with rationale, Scope cuts, Acceptance criteria sketch, Implementation checklist). This block is the producer half of a producer/consumer contract: `ralph-task` copies it verbatim into each new task's `-d`, so the brainstorm itself never appears in any task body. The implementer (human or autonomous Ralph) reads only the task; `ralph-review` reads the brainstorm/PRD as intent. Independence between contract and intent is what makes the cross-task review meaningful.

**Branching after Phase 3 — when do you need a PRD?** Once the brainstorm is saved, choose the next step by the Q4 heuristic:

- **Single-task or independent-sibling work** — skip Step 2. Hand the "Distilled for ralph-task" block straight to `ralph-task` (see Workflow Step 4 / `ralph-task` skill). No PRD layer needed.
- **Multi-task feature with cross-task invariants** — shared interface contract, ordering constraint, or any invariant the reviewer must check across tasks. Generate a PRD via `ralph-prd` (Step 2), then convert via `ralph-backlog` (Step 3).

When in doubt: if the brainstorm has cross-task invariants the reviewer must check across more than one task, you want a PRD.

### 2. Create a PRD

Use the PRD skill to generate a detailed requirements document:

```
Load the ralph-prd skill and create a PRD for [your feature description]
```

Answer the clarifying questions. The skill saves output to `design/[feature-name]-prd.md`.

### 3. Convert PRD to backlog tasks

Use the Ralph backlog skill to convert the markdown PRD to backlog tasks:

```
Load the ralph-backlog skill and convert design/[feature-name]-prd.md to backlog tasks
```

This creates individual backlog tasks with acceptance criteria, priorities, and dependencies.

### 4. Run Ralph

```bash
# Using Claude Code (default)
./scripts/ralph/ralph.sh [max_iterations]

# Using Claude Code with low effort (faster, cheaper)
./scripts/ralph/ralph.sh --tool claude --effort low [max_iterations]

# Using opencode
./scripts/ralph/ralph.sh --tool opencode [max_iterations]

# Run in sandboxed devcontainer
./scripts/ralph/ralph.sh --devcontainer [max_iterations]

# With error handling options
./scripts/ralph/ralph.sh --on-error retry --retry-count 3 --log-file ralph.log
```

Default is 10 iterations. Use `--tool claude` (default) or `--tool opencode` to select your AI coding tool. Add `--devcontainer` to run in an isolated container with network restrictions.

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--tool <claude\|opencode>` | AI tool to use | `claude` |
| `--model <model_id>` | Model ID for Claude Code | `claude-opus-4-8` |
| `--effort <level>` | Thinking effort for Claude Code: `low`, `medium`, `high`, or `max` | `medium` |
| `--timeout <minutes>` | Per-iteration timeout in minutes | `15` |
| `--on-error <strategy>` | How to handle AI tool errors: `stop`, `continue`, or `retry` | `stop` |
| `--retry-count <n>` | Number of retries when `--on-error=retry` | `2` |
| `--log-file <path>` | Log errors to file for later analysis | (none) |
| `--prompt-file <path>` | File to load prompt template from | (none) |
| `--tasks <ids>` | Comma-separated numeric task IDs to run (e.g. `62,64,65`). Mutually exclusive with `--prompt-file` | (none) |
| `--devcontainer` | Run inside a devcontainer | off |
| `--no-push` | Opt out of pushing `master` to `origin` after the loop finishes (see [Publishing to origin](#publishing-to-origin)) | push on |
| `--help` | Show help message and exit | |
| `--version` | Show version and exit | |

**`/ralph-run` skill options** (when launching from an interactive Claude Code session):

| Option | Description | Default |
|--------|-------------|---------|
| `watch` | Auto-monitor Ralph after launch. Accepts `true` (= `5m`), `false`, or a duration like `30s`, `5m`, `1h`. Schedules a self-paced status-watch loop via `ScheduleWakeup` to poll status and surface interesting events (failed iteration, stuck, crashed, finished). | none (no monitoring) |

**Strategies:**

- **stop** (default): Immediately exit on any error. Best for production runs where you want to investigate failures manually.
- **continue**: Log the error and proceed to the next iteration. Useful for long overnight runs where you want to maximize progress.
- **retry**: Retry failed iterations up to N times before giving up. Good for transient network issues or rate limits.

### Publishing to origin

Each iteration merges its task branch to **local** `master`. So that those merges become visible to anything reading the GitHub remote (e.g. a downstream consumer that treats `origin/master` as canon), the orchestrator publishes `master` to `origin` **by default** once the loop finishes.

The push is attempted only when **all** of these hold:

- push is not opted out (neither `--no-push` nor a truthy `RALPH_NO_PUSH` env var), **and**
- an `origin` remote is registered, **and**
- the loop actually advanced `master` — the `git rev-parse master` SHA taken before the loop differs from the one after it.

If no `origin` remote exists, or `master` did not move, the run skips the push cleanly (no push, no error). When a push **is** attempted and fails, the failure is surfaced loudly — logged to stderr and reflected in a non-zero exit code — never silently swallowed.

To disable the push for a single run, pass `--no-push` or set `RALPH_NO_PUSH=1`:

```bash
# Run without publishing to origin
./ralph.sh --no-push

# Same, via environment
RALPH_NO_PUSH=1 ./ralph.sh
```

### Releasing plugin updates (version bump)

This repo is its own plugin marketplace. Claude Code runs the plugin's skills from an on-disk cache at `~/.claude/plugins/cache/dddpaul-ralph/ralph/<version>/`, and `/plugin update` rebuilds that cache **only when it detects a new version**. The plugin version therefore acts as the cache-refresh trigger.

> **⚠️ Stale-cache warning:** if you change a shipped skill/agent but leave the version untouched, `/plugin update` no-ops and every consumer keeps running the **old** cached skills — silently. (Real incident 2026-07-26: a cached `ralph-stop` skill was a release behind, missing graceful-drain and whole subsystems, while the dev repo, GitHub, and the marketplace had all advanced.)

**Release / refresh procedure**

1. Bump the version in **both** manifests to the same value:
   - `plugins/ralph/.claude-plugin/plugin.json` → `version`
   - `.claude-plugin/marketplace.json` → `metadata.version`
2. Commit the bump together with the shipped change and merge to `master`.
3. Push `master` to `origin` (the Ralph loop does this by default; see above).
4. Consumers run `/plugin marketplace update dddpaul-ralph` then `/plugin update ralph@dddpaul-ralph` to pull the new version and rebuild their skill cache.

**Increment discipline** (human convention — the guard only enforces that the version moves *up*, not by how much):

- **patch** (`0.2.1`) — default: bug fixes and in-skill edits.
- **minor** (`0.3.0`) — a new skill/agent/flag, or a removed/renamed skill.
- **major** (`1.0.0`) — deferred to a future stable-surface declaration.

A `pre-push` git hook (`.claude/hooks/version-bump-guard.sh`, activated via a `.git/hooks/pre-push` wrapper) enforces this at the push boundary: if a push of `master` changes any shipped-set file (`plugins/ralph/skills/**`, `plugins/ralph/agents/**`, `plugin.json`, `marketplace.json`) without a strictly-greater version (`sort -V`), it is **blocked**. Non-master pushes, docs/tooling-only ranges, and the first push pass through. This guard is project-specific to this producer repo and is intentionally **not** part of the `ralph-init` template tree (seeded consumer projects ship no manifests).

**Examples:**

```bash
# Stop immediately on error (default behavior)
./ralph.sh --tool opencode

# Continue to next iteration on error, log to file
./ralph.sh --on-error continue --log-file errors.log

# Retry failed iterations up to 3 times
./ralph.sh --on-error retry --retry-count 3

# Launch from interactive Claude Code and auto-monitor every 5 minutes
/ralph-run watch=5m

# Launch with task whitelist and 2-minute monitoring interval
/ralph-run tasks=70 watch=2m max_iterations=3
```

Ralph will:
1. Check for remaining "To Do" tasks via `backlog task list`
2. Pick the next task (lowest ID or highest priority)
3. Create a branch (`task-<id>-description`) from master
4. Implement the task
5. Run quality checks (build, lint, tests)
6. Commit code, then run mandatory code review
7. Mark task as "Done", commit task file
8. Merge to master and delete the task branch
9. Repeat until all tasks are done or max iterations reached

Each iteration gets a `MODE: autonomous` prefix so the agent knows it's running in the Ralph loop vs interactive mode.

### 5. Cumulative review (recommended)

After Ralph completes the in-scope tasks, run the review skill to score the bundle of completed work against the upstream intent:

```
/ralph-review name=<feature-name>
```

The skill reads `design/<name>-prd.md` and `design/<name>-brainstorm.md`, evaluates the completed tasks against the original requirements, and writes a scored review to `design/<name>-review-<YYYY-MM-DD>.md`.

Step 6 of the review also runs a distillation **soft warning** scan: it greps each in-scope task `-d` for `design/.*-brainstorm\.md` and emits one warning line per match in the chat output ("Warning: TASK-NNN references a brainstorm file in its description — distillation may have been skipped"). The warning is informational; it does NOT block or alter the verdict. If the producer/consumer contract held — `ralph-task` self-checked at create-time and `task-reviewer` rule R16 caught any leak pre-merge — the soft warning will not fire. It is post-hoc insurance against pipeline regressions.

## Dual Mode: Autonomous + Interactive

CLAUDE.md serves both autonomous (Ralph loop) and interactive (human-driven) development:

- **Autonomous mode**: Ralph loop prepends `MODE: autonomous` to the prompt. The agent picks tasks from the backlog and works through them.
- **Interactive mode**: No mode prefix. The agent creates a backlog task for every code change request before implementing. Before implementing any task, it hits the **Implementation Mode Gate** — an `AskUserQuestion` prompt asking how to run it: **Ralph** (default/recommended — launch `/ralph-run` so Ralph branches, implements, reviews, and merges autonomously) or **Interactive** (branch and run the Task Lifecycle in the current session). Autonomous runs skip the gate; the loop is already the execution mode.

The same workflow (branch, implement, review, merge) applies in both modes.

## Key Files

| File | Purpose |
|------|---------|
| `ralph.sh` | Thin shim that execs the canonical Python orchestrator via `uv run` (supports `--tool claude\|opencode` and `--devcontainer`) |
| `CLAUDE.md` | Agent instructions for Claude Code (autonomous + interactive) |
| `.claude-plugin/marketplace.json` | Marketplace manifest — defines the `dddpaul-ralph` marketplace and its one `ralph` plugin |
| `plugins/ralph/` | The `ralph` plugin (`.claude-plugin/plugin.json` manifest) — bundles all `ralph-*` skills and both agents |
| `plugins/ralph/agents/` | Plugin-bundled agents: `task-reviewer` and `ralph-reviewer` |
| `backlog/` | Task files managed by backlog.md CLI |
| `.devcontainer/` | DevContainer configuration with firewall for sandboxed execution |
| `plugins/ralph/skills/ralph-init/` | Skill for bootstrapping Ralph in a new project |
| `plugins/ralph/skills/ralph-prd/` | Skill for generating PRDs |
| `plugins/ralph/skills/ralph-backlog/` | Skill for converting PRDs to backlog tasks |
| `plugins/ralph/skills/ralph-run/` | Skill for launching Ralph in the background from an interactive session |
| `plugins/ralph/skills/ralph-status/` | Skill for checking Ralph agent progress |
| `plugins/ralph/skills/ralph-status-watch/` | Internal skill for auto-monitoring Ralph via `ScheduleWakeup` (used by `watch` parameter) |
| `plugins/ralph/skills/ralph-stop/` | Skill for stopping a running Ralph agent |
| `flowchart/` | Interactive visualization of how Ralph works |

## Flowchart

[![Ralph Flowchart](ralph-flowchart.png)](https://snarktank.github.io/ralph/)

**[View Interactive Flowchart](https://snarktank.github.io/ralph/)** - Click through to see each step with animations.

The `flowchart/` directory contains the source code. To run locally:

```bash
cd flowchart
npm install
npm run dev
```

## Critical Concepts

### Each Iteration = Fresh Context

Each iteration spawns a **new AI instance** (Claude Code or opencode) with clean context. The only memory between iterations is:
- Git history (commits from previous iterations)
- Backlog task notes (learnings and context)
- CLAUDE.md / AGENTS.md files (reusable patterns)

### Small Tasks

Each backlog task should be small enough to complete in one context window. If a task is too big, the LLM runs out of context before finishing and produces poor code.

Right-sized tasks:
- Add a database column and migration
- Add a UI component to an existing page
- Update a server action with new logic
- Add a filter dropdown to a list

Too big (split these):
- "Build the entire dashboard"
- "Add authentication"
- "Refactor the API"

### Per-Task Branching

Each task gets its own branch (`task-<id>-description`) created from master. After the task is complete, code review passes, and quality checks pass, the branch is merged back to master and deleted. This keeps master always up-to-date and avoids long-lived feature branches.

### Mandatory Code Review

Every task branch is reviewed before merging. The agent spawns the `task-reviewer` agent to check acceptance criteria, functionality, security, code style, and test coverage. Only approved branches get merged.

### Git Hooks

The post-commit hook appends commit hashes to task files on `task-*` branches. This creates an audit trail linking commits to tasks. Use `--append-notes` (never `--notes`) to avoid overwriting hook-generated content.

A `pre-push` hook additionally guards the publish boundary: pushing `master` with a shipped skill/agent change but no version bump is blocked, so `/plugin update` always has a new version to rebuild the consumer cache from. See [Releasing plugin updates](#releasing-plugin-updates-version-bump).

### AGENTS.md / CLAUDE.md Updates

After each iteration, Ralph updates the relevant AGENTS.md or CLAUDE.md files with learnings. This is key because AI coding tools automatically read these files, so future iterations (and future human developers) benefit from discovered patterns, gotchas, and conventions.

### Feedback Loops

Ralph only works if there are feedback loops:
- Build/typecheck catches compilation errors
- Linter enforces code style
- Tests verify behavior
- Code review catches issues before merge
- CI must stay green (broken code compounds across iterations)

### Stop Condition

When all tasks have status "Done" (no "To Do" tasks remaining), Ralph outputs `<promise>COMPLETE</promise>` and the loop exits.

### Heartbeat Liveness

Ralph writes a heartbeat file (`backlog/.ralph-heartbeat`) every 5 seconds while running. The `ralph-status` and `ralph-run` skills use this file to determine whether Ralph is actually alive — if the heartbeat hasn't been updated within 15 seconds, Ralph is considered dead regardless of what the status file says. This replaces `kill -0` PID checks, which can give false positives when PIDs are reused or the process runs in a container.

### Shim and Canonical Orchestrator

Each project carries a thin `ralph.sh` shim that execs the canonical Python orchestrator bundled by the `ralph` plugin at `plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py` (run via `uv run`). The shim resolves the orchestrator by precedence (`$RALPH_ORCHESTRATOR` explicit override, then the newest installed plugin-cache copy, else a clear install-the-plugin error), so a detached `nohup ./ralph.sh` finds the orchestrator from the installed plugin without `${CLAUDE_PLUGIN_ROOT}`. When launching Ralph, the `ralph-run` skill searches for the project shim in priority order:

1. `./ralph.sh` — project root (created by `ralph-init`)
2. `scripts/ralph/ralph.sh` — structured project location

The shim sets `RALPH_PROJECT_ROOT` and delegates to the canonical orchestrator, so all projects share one implementation while keeping project-relative paths correct. Run `/ralph-init` to bootstrap the shim in a new project.

### Devcontainer plugin-cache reachability

The plugin-cache resolver tier (the newest `/plugin install` under `$CLAUDE_CONFIG_DIR/plugins/cache`) also works inside the DevContainer. The `.devcontainer/devcontainer.json` mount `source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind` bind-mounts the **entire** host `~/.claude` — including `plugins/cache/` — onto `CLAUDE_CONFIG_DIR=/home/node/.claude`. So a plugin the host installs with `/plugin install ralph@dddpaul-ralph` is reachable inside the container, and the shim's plugin-cache glob (`$CLAUDE_CONFIG_DIR/plugins/cache/*/ralph/*/skills/ralph-run/scripts/ralph_orchestrator.py`) finds it. No extra mount is required — the existing whole-directory bind covers the `plugins/` subtree.

To smoke-test this from a shell **inside the container**:

```bash
# 1. Mount check — the host plugin cache is reachable under CLAUDE_CONFIG_DIR:
ls -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache"
# -> /home/node/.claude/plugins/cache

# 2. Resolver check — the plugin-cache tier resolves the orchestrator from a
#    plugin-cache layout. A scratch config dir + scratch shim copy (no
#    $RALPH_ORCHESTRATOR override) plus a stub `uv` that echoes the resolved path
#    instead of launching the loop. This mirrors what `/plugin install` lays down.
tmp="$(mktemp -d)"
cp ./ralph.sh "$tmp/ralph.sh"
orch="$tmp/cfg/plugins/cache/dddpaul-ralph/ralph/v1.0.0/skills/ralph-run/scripts/ralph_orchestrator.py"
mkdir -p "$(dirname "$orch")" && : > "$orch"
mkdir -p "$tmp/bin"
printf '#!/usr/bin/env bash\nshift\necho "RESOLVED=$1"\n' > "$tmp/bin/uv"
chmod +x "$tmp/bin/uv"
PATH="$tmp/bin:$PATH" CLAUDE_CONFIG_DIR="$tmp/cfg" bash "$tmp/ralph.sh" --help
# -> RESOLVED=<tmp>/cfg/plugins/cache/dddpaul-ralph/ralph/v1.0.0/skills/ralph-run/scripts/ralph_orchestrator.py
rm -rf "$tmp"
```

Both lines confirm the plugin-cache tier is reachable in the container: step 1 proves the mount exposes the cache, step 2 proves the resolver traverses that exact layout. If the `ralph` plugin is actually installed on the host, you can confirm the real mounted install resolves too:

```bash
ls "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/ralph/*/skills/ralph-run/scripts/ralph_orchestrator.py
```

### Double-Run Guard

Ralph refuses to start if another instance is already running. On startup, it checks the status file (`backlog/.ralph-status.json`) — if the state is `"running"` and the heartbeat file is fresh (updated within 15 seconds), Ralph exits with an error. This prevents two instances from picking the same task or creating conflicting branches.

### Status File (`.ralph-status.json`)

Ralph writes `backlog/.ralph-status.json` on every state change. External consumers (dashboards, scripts, the `ralph-status-watch` skill) can read this file to track progress.

```json
{
  "pid": 99222,
  "started_at": "2026-05-01T08:50:16Z",
  "state": "running",
  "iteration": 2,
  "max_iterations": 10,
  "tool": "claude",
  "tasks_done": ["TASK-62"],
  "tasks_remaining": 3,
  "current_task": "TASK-64",
  "last_iteration_duration": 142,
  "elapsed": 300,
  "errors": [
    { "iteration": 1, "at": "2026-05-01T08:52:00Z", "message": "timeout after 900s" }
  ],
  "completed_at": null,
  "exit_code": null,
  "iteration_started_at": "2026-05-01T08:55:16Z",
  "timeout_sec": 900
}
```

Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `iteration_started_at` | ISO 8601 string \| `null` | Timestamp when the current iteration began |
| `timeout_sec` | number | Per-iteration timeout in seconds |
| `errors` | array of objects | Each error is `{ "iteration": <int>, "at": "<ISO 8601>", "message": "<string>" }` |

**Breaking change:** `errors` was previously an array of bare strings. It is now an array of objects with `iteration`, `at`, and `message` fields. Scripts or dashboards that parse this field will need to be updated.

### --help and --version

Ralph supports `--help` to show usage information and `--version` to print the current version string (e.g., `ralph.sh 0.5.0`). Both flags exit immediately without starting the loop.

## Debugging

Check current state:

```bash
# See all tasks and their status
backlog task list --plain

# See details of a specific task
backlog task <id> --plain

# Check git history
git log --oneline -10
```

## Testing

Ralph has two test suites, split by language:

- **Bash tests ([bats-core](https://github.com/bats-core/bats-core))** cover the bash surface — the `ralph.sh` shim, git hooks (pre-commit, commit-msg), PreToolUse guard hooks, argument/dependency checks, and the end-to-end backlog workflow. Run via `npm test`, which invokes `bats tests/unit tests/integration tests/e2e`.
- **Python tests ([pytest](https://docs.pytest.org/))** cover the orchestrator (`plugins/ralph/skills/ralph-run/scripts/ralph/*.py`) — argument parsing, the iteration loop, heartbeat, status file, preflight, usage checks, tool wrappers (claude/opencode), summary, and signal handling. Run via `uv run pytest`.

### Bash tests (bats)

Install bats-core:

**Option 1: npm (recommended)**

```bash
npm install
```

**Option 2: System-wide installation**

See [bats-core installation guide](https://github.com/bats-core/bats-core#installation) for your platform.

Run them:

```bash
# Run all bash tests (bats over tests/unit, tests/integration, tests/e2e)
npm test

# Run unit tests only
npm run test:unit

# Run integration tests only
npm run test:integration

# Run E2E tests
npm run test:e2e
```

### Python tests (pytest)

The orchestrator suite lives at `plugins/ralph/skills/ralph-run/tests/test_*.py`; test paths and `pythonpath` are configured in `pyproject.toml`. Run it with uv:

```bash
# Run the full orchestrator suite
uv run pytest

# Run a single test file
uv run pytest plugins/ralph/skills/ralph-run/tests/test_loop_exit_code.py
```

### Test layout

**Bash (`tests/`)** — run by `npm test`:

- `tests/unit/` - Unit tests for individual bash functions and hooks
  - `argument-validation.bats` - Validates CLI arguments (--tool, --devcontainer, max_iterations)
  - `commit-msg-hook.bats` - Tests the commit-msg hook (forbidden-trailer / scissor-line handling)
  - `dependency-checks.bats` - Tests dependency verification (git, backlog CLI, AI tools)
  - `pre-commit-hook.bats` - Tests the pre-commit hook (NFC/NFD filename normalization)
  - `pretools-hooks.bats` - Tests PreToolUse guard hooks (blocks forbidden commit trailers)
  - `run-summary.bats` - Tests run summary generation
  - `status-file.bats` - Tests status file creation and updates
  - `usage-check.bats` - Tests the usage/quota check (ccusage block-end buffer)
- `tests/integration/` - Integration tests for component interactions
  - `completion-signal.bats` - Tests `<promise>COMPLETE</promise>` detection and loop termination
  - `interrupt-trap.bats` - Tests signal handling and graceful shutdown on interrupt
  - `on-error-continue.bats` - Tests the `--on-error continue` strategy across failed iterations
  - `one-task-enforcement.bats` - Tests that each iteration completes exactly one task
  - `prompt-generation.bats` - Tests prompt template loading and MODE: autonomous prefix injection
  - `run-summary-integration.bats` - Tests run summary across multiple iterations
  - `shim.bats` - Tests that the `ralph.sh` shim matches the canonical orchestrator
  - `status-file-integration.bats` - Tests status file updates across iterations
  - `tee-buffering.bats` - Tests output buffering with tee
  - `timeout-handling.bats` - Tests iteration timeout and graceful shutdown
  - `usage-pause.bats` - Tests preflight pausing the launch when usage limits are near
- `tests/e2e/` - End-to-end tests for full workflows with real backlog tasks
  - `backlog_workflow.bats` - End-to-end test of the full backlog task workflow
- `tests/helpers/` - Shared test utilities and mocks (`common.bash`)

**Python (`plugins/ralph/skills/ralph-run/tests/`)** — run by `uv run pytest`:

- Argument & prompt handling - `test_orchestrator_args.py`, `test_prompts.py`
- Iteration loop - `test_loop_*.py` (exit codes, summaries, task whitelist, run log, devcontainer launch, signal interrupts)
- Heartbeat & status file - `test_heartbeat.py`, `test_wait_heartbeat.py`, `test_status.py`
- Preflight & usage checks - `test_preflight.py`, `test_usage_check.py`, `test_usage_wrapper.py`
- Tool wrappers - `test_tool_claude.py`, `test_tool_opencode.py`, `test_tools.py`
- Devcontainer, signals, summary, task selection, end-to-end - `test_devcontainer.py`, `test_signals.py`, `test_summary.py`, `test_tasks.py`, `test_e2e_fake_claude.py`

## Customizing

After copying `CLAUDE.md` to your project, customize it:
- Add project-specific quality check commands
- Include codebase conventions and common gotchas
- Add language/framework instructions to the `## Project-Specific` section at the bottom of CLAUDE.md

## References

- [Geoffrey Huntley's Ralph article](https://ghuntley.com/ralph/)
- [Backlog.md CLI](https://github.com/MrLesk/Backlog.md)
- [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code)
- [opencode documentation](https://opencode.ai/docs)

## Troubleshooting

### Common issues

**opencode not found**

Ensure opencode is installed globally and in your PATH:
```bash
npm install -g @opencode/cli
which opencode  # Should return the path
```

**Tests fail with "bats: command not found"**

Install bats-core dependencies:
```bash
npm install
# Or install bats-core system-wide
```

**Git repository not initialized**

Ralph requires a git repository. Initialize one if needed:
```bash
git init
git add .
git commit -m "Initial commit"
```

**Backlog CLI not found**

Install the Backlog.md CLI:
```bash
# See https://github.com/MrLesk/Backlog.md for installation instructions
```

**Context window exceeded**

If a task is too large for a single context window, split it into smaller subtasks. Ralph works best with small, focused tasks (see "Small Tasks" section above).

**Merge conflicts on task branches**

If a task branch has conflicts with master:
1. Rebase onto master: `git rebase master`
2. Resolve conflicts
3. Continue: `git rebase --continue`
4. Run tests to verify the fix

**Tests timing out**

Increase timeout values in test files if needed, or check for hanging processes. E2E tests may take longer on slower systems.
