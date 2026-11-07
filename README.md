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

**Common allow rules:** a plugin cannot ship allow rules, so `plugins/ralph/user-settings.json` holds the common ones for your user settings (`~/.claude/settings.json`): 46 `Bash(...)` rules, `ScheduleWakeup`, `attribution` with an empty commit and PR trailer, and `sandbox` with `enabled` and `autoAllowBashIfSandboxed`. It holds no `Skill(...)` rules, because plugin skills need none. The `/ralph-run` preflight lists the entries your user settings miss in one warning and changes no file. To add them, run `bash <installPath>/skills/ralph-run/scripts/merge-user-settings.sh ~/.claude/settings.json` (configuration management can run it too). It appends missing entries, keeps every other key, and reports a differing value on stderr without overwriting it.

**Updating:** re-run `/plugin marketplace add dddpaul/ralph` (or `/plugin update ralph@dddpaul-ralph`) to pull the latest version. The user owns `~/.claude/`: `ralph-init` writes to it only when you agree to merge the fragment above into `settings.json` (Init Step 3.7a, Upgrade U4).

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

**Shared project `.claude`:** `workspaceMount` bind-mounts the project folder at `/workspace`, so the container reads the project's own `.claude/` — skills, hooks, and `CLAUDE.md` are the same bytes on both sides and a container-side commit can never revert a host edit. Only `.claude/settings.local.json` is overridden, by a single-file bind of `.devcontainer/container-settings.local.json` (`{"sandbox": {"enabled": false}}` — `bwrap` cannot create mount namespaces on Docker Desktop macOS, so the sandbox must be off in the container while the host keeps it on). An `initializeCommand` seeds the host `.claude/settings.local.json` when it is missing or empty, otherwise Docker would create the bind destination as an unparsable 0-byte file. `postCreateCommand` runs `git config --global --add safe.directory /workspace`: `/workspace` presents as root-owned inside the container while the user is `node`, so without it git refuses the repo with `detected dubious ownership` and Ralph gets no `status` and no `commit`.

**User `~/.claude` bound twice (so plugin agents resolve):** `devcontainer.json` binds the host `~/.claude` both at `/home/node/.claude` (the `$HOME` alias) and at its own host path, `source=${localEnv:HOME}/.claude,target=${localEnv:HOME}/.claude,type=bind`. The second bind is not a duplicate: Claude Code's plugin registries (`plugins/known_marketplaces.json`, `plugins/installed_plugins.json`) record absolute **host** paths, so a marketplace resolves only when that literal path also exists inside the container. Without it every user plugin fails with `Marketplace <name> failed to load: cache-miss` and the `task-reviewer` agent from `ralph@dddpaul-ralph` never registers — the Review step then degrades to a plain agent reading a rules file while still reporting APPROVED. Verify inside the container with `claude plugin list` (expect `enabled`, not `cache-miss`) and `claude plugin details ralph@dddpaul-ralph` (expect `Agents (2) task-reviewer, ralph-reviewer`); both work without auth. `CLAUDE_CONFIG_DIR` points at that same host path (`${localEnv:HOME}/.claude`), not at `/home/node/.claude`, so the container writes the shared registries under the root the host can read back: rooted at `/home/node` a container run relocates `installLocation` / `installPath` to a path that does not exist on the host, and the host then rejects the entry with `corrupted installLocation (/home/node/...) — expected a path inside <config>/plugins/marketplaces` for **every** marketplace, not just ralph's. Both names are binds of the same directory, so the `/home/node/.claude` bind stays as the `$HOME` alias for anything that ignores `CLAUDE_CONFIG_DIR`. Being a mount and a `containerEnv` entry, this applies only on a **container recreate**.

**Host `.venv` isolation:** `workspaceMount` bind-mounts the project folder at `/workspace`, so a container-side `uv sync` would otherwise write a Linux interpreter path into the host's `.venv/pyvenv.cfg` and leave `.venv/bin/python3` dangling on the host. `devcontainer.json` mounts a named volume over that one path (`source=claude-code-project-venv-${devcontainerId},target=/workspace/.venv,type=volume`, chowned to `node` in `postCreateCommand`), so the container builds its own virtualenv and the host keeps its own. Mount changes need a **container rebuild**, not a restart — pass `--rebuild` alongside `--devcontainer` (or `/ralph-run rebuild=true`) to recreate the container; if an earlier run already clobbered the host venv, repair it once with `rm -rf .venv && uv sync` on the host.

**Claude Code version is pinned:** `devcontainer.json` passes `CLAUDE_CODE_VERSION` as a concrete `X.Y.Z` build arg, not `latest`. The npm install layer is cached, so a floating tag is resolved once and then frozen — the container's CLI silently ages until it rejects a newer model (`Claude Code X.Y.Z does not support this model`). Bump the pin to `npm view @anthropic-ai/claude-code version`; the changed value invalidates the npm layer and the layers after it (not the ones before) on the next build, and the build fails on a non-`X.Y.Z` value and checks `claude --version` against it. `grep '"CLAUDE_CODE_VERSION"' .devcontainer/devcontainer.json` shows what the next build installs; `docker image inspect --format '{{ index .Config.Labels "dev.ralph.claude-code-version" }}' <image>` shows what a built image carries (images are named `vsc-<folder>-<hash>`). `--rebuild` / `--remove-existing-container` recreates the **container** only and does NOT refresh the image — run `devcontainer build --workspace-folder . --no-cache` to force a fresh one.

**uv version is pinned:** `devcontainer.json` also passes `UV_VERSION` as a concrete `X.Y.Z` build arg. uv runs the orchestrator, installs the interpreter and executes every PEP 723 script, so a frozen copy shows up as a confusing resolver error rather than an obvious stale-tool one. Because `COPY --from` cannot expand a build arg, uv is pulled through a pinned stage (`FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin`) and copied once, in the base, for every language. `grep '"UV_VERSION"' .devcontainer/devcontainer.json` shows what the next build installs; `docker image inspect --format '{{ index .Config.Labels "dev.ralph.uv-version" }}' <image>` shows what a built image carries. One consequence: a plain `docker build` now needs `--build-arg UV_VERSION=<X.Y.Z>`, or the stage reference is `ghcr.io/astral-sh/uv:` and Docker fails with an opaque `invalid reference format` — the `devcontainer` CLI supplies it from `devcontainer.json`, so the normal path is unaffected.

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
| `--model <model_id>` | Model ID for Claude Code | `claude-opus-5-5` |
| `--effort <level>` | Thinking effort for Claude Code: `low`, `medium`, `high`, or `max` | `medium` |
| `--timeout <minutes>` | Per-iteration timeout in minutes | `15` |
| `--on-error <strategy>` | How to handle AI tool errors: `stop`, `continue`, or `retry` | `stop` |
| `--retry-count <n>` | Number of retries when `--on-error=retry` | `2` |
| `--log-file <path>` | Log errors to file for later analysis | (none) |
| `--prompt-file <path>` | File to load prompt template from | (none) |
| `--tasks <ids>` | Comma-separated numeric task IDs to run (e.g. `62,64,65`). Mutually exclusive with `--prompt-file` | (none) |
| `--devcontainer` | Run inside a devcontainer | off |
| `--rebuild` | With `--devcontainer`, recreate the container from scratch (`devcontainer up --remove-existing-container`) so `devcontainer.json` mount/config changes take effect. Does **not** refresh cached image layers — use `devcontainer build --workspace-folder . --no-cache` for that. No-op without `--devcontainer`. Without it, a `--devcontainer` launch whose existing container is older than `.devcontainer/devcontainer.json` or `.devcontainer/Dockerfile` (container `Created` vs file mtime, looked up by the `devcontainer.local_folder` label) **refuses to start** and prints both timestamps plus this remedy; the probe is skipped silently when docker or the container is unavailable | off |
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

A `pre-push` git hook (`.claude/hooks/version-bump-guard.sh`, activated via a `.git/hooks/pre-push` wrapper) enforces this at the push boundary: if a push of `master` changes any shipped-set file (`plugins/ralph/skills/**`, `plugins/ralph/agents/**`, `plugins/ralph/hooks/**`, `plugins/ralph/user-settings.json`, `plugin.json`, `marketplace.json`) without a strictly-greater version (`sort -V`), it is **blocked**. Non-master pushes, docs/tooling-only ranges, and the first push pass through. This guard is project-specific to this producer repo and is intentionally **not** part of the `ralph-init` template tree (seeded consumer projects ship no manifests).

The same hook also checks release tags: the release commit of `vX.Y.Z` is the first commit along origin's `master` first-parent history where both manifests read `X.Y.Z` (or, for a merge pull of another host's release, that release), and origin's tag (peeled) must point there. It refuses the push when origin tags that version elsewhere (two hosts released the same version with different content), when the two manifests disagree on the pushed tip, or when `git ls-remote origin` does not answer within `VERSION_GUARD_LS_REMOTE_TIMEOUT` seconds (default 20). An existing tag is never moved; the manual re-bump is in [`.claude/RELEASING.md`](.claude/RELEASING.md).

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

Step 6 of the review also runs a distillation **soft warning** scan: it greps each in-scope task `-d` for `design/.*-brainstorm\.md` and emits one warning line per match in the chat output ("Warning: TASK-NNN references a brainstorm file in its description — distillation may have been skipped"). The warning is informational; it does NOT block or alter the verdict. If the producer/consumer contract held — `ralph-task` self-checked at create-time and the `task-reviewer` agent's built-in rule R-CORE-5 caught any leak pre-merge — the soft warning will not fire. It is post-hoc insurance against pipeline regressions.

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
| `plugins/ralph/hooks/` | Plugin-delivered Claude guard hooks: `hooks.json`, the `run.sh` marker-gate dispatcher and the seven guards |
| `plugins/ralph/git-hooks/` | Plugin-delivered git hook bodies (`pre-commit`, `commit-msg`, `post-commit`, and `pre-push` for shared-backlog clones), run through the per-clone shim |
| `plugins/ralph/user-settings.json` | The common allow rules, `attribution` and `sandbox` for the user settings file |
| `backlog/` | Task files managed by backlog.md CLI |
| `scripts/shorten-backlog-filenames.py` | Remediation for backlog filenames already over the 125-byte cap, across one project or a whole tree of them (dry-run by default, `--apply` renames via `git mv` and commits each project) |
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

Every task branch is reviewed before merging. The agent spawns the `task-reviewer` agent to check acceptance criteria, functionality, security, code style, and test coverage. The reviewer verifies each acceptance criterion itself and lists evidence for every AC it counts as met — a command it ran plus the relevant output lines, a `file:line` quote, or a rendered image or crop path; an AC without evidence is reported as NOT met, and the author's own notes or summary do not count. Findings are classified as blocking (unmet AC, built-in or loaded-rule violation named by rule ID, correctness, bugs, security, unintended changes) or minor (unruled style remarks), and the verdict follows a fixed rubric: APPROVED iff there are zero blocking findings (SCORE = 10 − minor, floor 7), otherwise CHANGES REQUESTED (SCORE = 5 − (blocking − 1), floor 1). The report's last line is `SCORE: N`. Six review-conduct rules ship built into the agent and apply in every project, with or without a rules file: `R-CORE-1` review the diff, not the working tree (git is the truth); `R-CORE-2` every AC checked or explicitly deferred; `R-CORE-3` rationalization is not exemption; `R-CORE-4` content preservation during moves; `R-CORE-5` no brainstorm-file references in task descriptions; `R-CORE-6` a changed external-tool default needs an invocation AC. Being part of the plugin, they reach a project on the next plugin update, without a `ralph-init upgrade`. The shared `R-DOCS-*` documentation rules ship the same way, as a bundle the agent reads from its own plugin root (`plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.docs.md`); a project opts in or out with `docs_rules=on` / `docs_rules=off` in `.claude/task-reviewer.conf`, and without that setting the rules apply iff the project has an `.obsidian/` vault. The `R-INFRA-*` rules for the files ralph-init installs in every project — agent frontmatter (`R-INFRA-1`, `R-INFRA-2`), GNU/BSD and macOS bash 3.2 shell portability (`R-INFRA-3`), no over-broad shell permissions (`R-INFRA-4`), hooks calling scripts rather than inline bash (`R-INFRA-5`), not bypassing the master-branch guard (`R-INFRA-6`) and PostToolUse JSON via `hookSpecificOutput` (`R-INFRA-7`) — ship as a second bundle beside it (`plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md`), switched by `infra_rules=on` / `infra_rules=off` in the same file; without that setting they apply iff the project has a `ralph.sh` shim at its root or at `scripts/ralph/ralph.sh`. On top of them the agent adds `~/.claude/task-reviewer-rules.md` (user-global) and the project's own `.claude/task-reviewer-rules.md`. ralph-init no longer copies the bundle into projects; `ralph-init upgrade` reports a leftover `.claude/task-reviewer-rules.docs.md` and removes it only when you agree, and the agent never reads it. A missing shipped bundle that applies is reported as a load error rather than skipped, and every report records the plugin version, the bundle paths and any rule IDs a project rule explicitly replaces. Only approved branches get merged.

### Git Hooks

The post-commit hook appends commit hashes to task files on `task-*` branches. This creates an audit trail linking commits to tasks. Use `--append-notes` (never `--notes`) to avoid overwriting hook-generated content.

A `pre-push` hook additionally guards the publish boundary: pushing `master` with a shipped skill/agent change but no version bump is blocked, so `/plugin update` always has a new version to rebuild the consumer cache from. See [Releasing plugin updates](#releasing-plugin-updates-version-bump).

The `pre-commit` hook runs the plugin's `hooks/filename-length-guard.sh` (a legacy copy in `.git/hooks` runs `.claude/hooks/filename-length-guard.sh`), which rejects any staged path whose name component exceeds 125 bytes (the ecryptfs sync target caps names at ~140 bytes and Syncthing adds 15 for its transfer name). The guard only blocks *new* names; to repair backlog files that are already over the cap, run the remediation script — it asks `claude -p` for a shorter semantic slug, keeps the `<type>-<id> - ` prefix, and leaves `title:` frontmatter alone (backlog.md addresses artifacts by `id:`, not by filename):

```bash
# Dry run: print planned old -> new for every over-limit backlog file
uv run scripts/shorten-backlog-filenames.py

# Apply the renames with git mv and commit them
uv run scripts/shorten-backlog-filenames.py --apply

# Sweep every project under a directory, committing to each one in turn
uv run scripts/shorten-backlog-filenames.py --path ~/projects --apply
```

It walks the live artifact directories `backlog/{tasks,docs,decisions,drafts,milestones}`; `--include-archive` adds `archive/` and `completed/`. Rows tagged `[FALLBACK]` mean claude returned nothing usable -- an error, a prose sentence, or a refusal such as `I cannot help` -- and the existing slug was truncated instead; `[COLLISION]` means a numeric suffix was added. A file git does not track yet -- the usual case, since the pre-commit guard is what blocked the commit that would have added it -- is renamed in place with a `NOTICE:` telling you to `git add` it, because `git mv` refuses an untracked path. Flags: `--limit`, `--model`, `--path`, `--include-archive`, `--no-verify`, `--timeout`.

`--path` names a *tree* to sweep, not necessarily a single backlog: every backlog root under it (a directory holding `config.yml` **and** one of the artifact directories) is discovered, grouped by the git repository that owns it, and renamed then committed on its own before the next project is touched. A monorepo with several backlogs is one project and takes one commit; a backlog in no repository is skipped with a warning. The default `--path backlog` is simply the one-project case of the same sweep.

Each project gets one pathspec-scoped commit of exactly the renamed paths, `chore(backlog): shorten N over-limit filename(s) for ecryptfs sync`, on whatever branch is checked out -- so work already staged in a repository the sweep passes through is never swept into it, and untracked renames stay out of the commit entirely. Commits respect that project's git hooks; `--no-verify` bypasses them, which is what a Ralph project's own commit-prefix guard on `master` will otherwise refuse. A project that fails to rename or commit is reported and the sweep moves on, and the run exits 1. The summary closes with `projects=<n> committed=<n> project-errors=<n>`.

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

Each project carries a thin `ralph.sh` shim that execs the canonical Python orchestrator bundled by the `ralph` plugin at `plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py` (run via `uv run`). The shim resolves the orchestrator by precedence (`$RALPH_ORCHESTRATOR` explicit override, then the plugin install Claude Code registered, else a clear install-the-plugin error), so a detached `nohup ./ralph.sh` finds the orchestrator from the installed plugin without `${CLAUDE_PLUGIN_ROOT}`. When launching Ralph, the `ralph-run` skill searches for the project shim in priority order:

1. `./ralph.sh` — project root (created by `ralph-init`)
2. `scripts/ralph/ralph.sh` — structured project location

The shim sets `RALPH_PROJECT_ROOT` and delegates to the canonical orchestrator, so all projects share one implementation while keeping project-relative paths correct. Run `/ralph-init` to bootstrap the shim in a new project.

### Plugin registry resolver

`ralph.sh` and `refine.sh` find the installed plugin through Claude Code's plugin registry, never by sorting cache folders (a `sort -V` over cache paths ranks the marketplace name above the version, so a fork called `ralph` or a leftover folder could win). The lookup is one shell block, `ralph_resolve_plugin <dir> <relpath>`, kept in `plugins/ralph/skills/ralph-init/templates/shims/resolve-plugin.sh`; every embedding copy must match it byte for byte (`tests/python/test_resolve_plugin.py`). It:

- finds `jq` on `PATH`, else at `git config ralph.jq`;
- reads `<config>/plugins/installed_plugins.json`, where the config dir is `$CLAUDE_CONFIG_DIR`, else `git config ralph.claudeConfigDir`, else `$HOME/.claude`, and requires `"version": 2`;
- takes only the `ralph@dddpaul-ralph` entries and, like Claude Code (observed on 2.1.309), picks the first one in registry order that applies: a `scope: "user"` entry applies everywhere, a `scope: "project"` or `scope: "local"` entry only where its `projectPath` equals the clone's identity. Claude Code appends new installs, so a user install made before a project install still wins inside the project;
- uses `git config ralph.projectPath` as the identity, else the main worktree root (the canonical parent of `git rev-parse --git-common-dir`), so a linked worktree resolves like its main clone; a separate-git-dir layout is rejected;
- fails with its own message for each of: no jq, no registry, invalid JSON, the wrong registry version, no applicable entry, no `installPath`, a missing `installPath` directory, and a missing target file.

**Inside the DevContainer** the `.devcontainer/devcontainer.json` mounts bind the **entire** host `~/.claude` at its own host path, which is where `CLAUDE_CONFIG_DIR` points, so the registry and the host paths it records are both reachable and a user-scope install resolves as on the host. The clone itself is mounted at `/workspace`, which never equals a host `projectPath`: a project-scope install matches there only when the clone's `git config ralph.projectPath` holds the host path (the config lives in `.git/config`, so it travels with the mount). To check the lookup from a shell inside the container:

```bash
. plugins/ralph/skills/ralph-init/templates/shims/resolve-plugin.sh
ralph_resolve_plugin . skills/ralph-run/scripts/ralph_orchestrator.py
# -> /Users/<user>/.claude/plugins/cache/dddpaul-ralph/ralph/<version>/skills/ralph-run/scripts/ralph_orchestrator.py
```

### Plugin guard hooks

The plugin ships the Claude guard hooks in `plugins/ralph/hooks/`: the seven guards (`commit-msg-guard`, `commit-prefix-guard`, `master-branch-guard`, `naming-guard`, `notes-guard`, `task-validator`, `filename-length-guard`) and a `hooks.json` with the same 13 entries and `if:` filters as the legacy `settings.json` that older ralph-init versions wrote into each project. Every entry runs `"${CLAUDE_PLUGIN_ROOT}"/hooks/run.sh <guard>`, a dispatcher that:

- resolves the session's git root from `$CLAUDE_PROJECT_DIR` (`git rev-parse --show-toplevel`, made canonical), so a session started in a subdirectory finds its root and a nested repository is its own root;
- exits 0 unless that root's tracked `.claude/ralph.json` has `"pluginHooks": true`, and exits 0 for a guard listed in its `localGuards` array;
- otherwise runs the guard from the payload's `cwd` with the hook input unchanged, exports `RALPH_PROJECT_ROOT`, and returns the guard's exit code. A bad guard name, a missing jq or an unreadable marker is a non-blocking error (exit 1).

Without the marker the plugin hooks do nothing, so a project keeps its legacy `.claude/hooks/` wiring, and the guards still work there: they take project paths from the git root of `RALPH_PROJECT_ROOT`, else of `$CLAUDE_PROJECT_DIR`. ralph-init no longer ships template copies of the guards; this repo's `.claude/hooks/` copies stay byte-identical to the plugin (`tests/python/test_plugin_hooks.py`, `tests/unit/template-parity.bats`).

### Plugin git hooks

The plugin ships the git hook bodies in `plugins/ralph/git-hooks/` (`pre-commit`, `commit-msg`, `post-commit`, `pre-push`). A clone runs them through one fixed shim, `plugins/ralph/skills/ralph-init/templates/shims/git-hook`, installed under each hook name in the directory `git rev-parse --git-path hooks` returns (which honours `core.hooksPath`). The shim:

- runs the clone's own `<name>.local` hook from that directory first, with the hook's arguments, and stops when it fails; for `pre-push` (and the other stdin-fed hooks `post-rewrite` and `reference-transaction`) it buffers stdin so both hooks read all of it;
- execs `<installPath>/git-hooks/<name>` found through the registry resolver above, with the same arguments;
- when the plugin cannot be resolved, prints the resolver's reason and then fails or warns per clone switch: `pre-commit` and `commit-msg` fail when `git config ralph.pluginHooks` is true and name `git commit --no-verify`; `pre-push` fails when `ralph.pluginHooks` or `ralph.sharedBacklog` is true and names `git push --no-verify`; `post-commit` and every hook with neither switch set only warn.

`pre-commit` runs the length guard bundled beside it (`plugins/ralph/hooks/filename-length-guard.sh`) and falls back to `<repo>/.claude/hooks/filename-length-guard.sh` when it runs as a legacy copy in `.git/hooks`. `pre-push` acts only in a clone whose trusted switch `git config ralph.sharedBacklog` is true (set by `shared-backlog.sh enable`, which installs the shim as pre-push), never on the marker: it runs the read-only `shared-backlog.sh check-dupes` on every pushed SHA, skips ref deletions and takes no lock, so a `create`, `claim` or `integrate` push that holds the protocol lock passes through it without deadlock. It refuses a tip with a duplicate task or draft ID, or when the `backlog` CLI is missing (`tests/shell/shared-backlog-prepush-test.sh`). `commit-msg` finds a merge in progress through `git rev-parse --git-path MERGE_MSG`, so it also works in a linked worktree. The `pre-commit`, `commit-msg` and `post-commit` bodies still work as legacy copies installed straight into `.git/hooks` (`tests/python/test_git_hook_shim.py`); ralph-init no longer ships template copies of them.

### Plugin-hooks migration

`ralph-init` copies no guard scripts, no git hook bodies and no common allow rules into a project. Instead, a project uses three things:

- **The marker.** The tracked file `.claude/ralph.json` with `"pluginHooks": true` is the project's ownership marker; it switches on the plugin guard hooks above. Its optional `localGuards` array names guards the project keeps as its own copies in `.claude/hooks/`, registered in its `.claude/settings.json`; the plugin skips those. `.gitignore` carries `!.claude/ralph.json` so the marker is committed.
- **The switches.** Per-clone git config, never committed:
  - `ralph.pluginHooks true` makes `pre-commit` and `commit-msg` block when the plugin cannot be resolved;
  - `ralph.jq` and `ralph.projectPath` (the host's canonical main worktree root) tell the resolver which jq to use and which clone it is;
  - `ralph.claudeConfigDir` is set only when the Claude config dir is not `~/.claude`;
  - `ralph.sharedBacklog` is never set by the migration: `scripts/shared-backlog.sh enable` sets it (with `ralph.holder`, the host's default holder, and the pre-push shim) in a project whose marker sets `"sharedBacklog": true`, and `disable` clears it. `scripts/shared-backlog.sh` is a fixed project shim (`templates/shims/shared-backlog.sh`) that execs the plugin's `scripts/shared-backlog.sh`. Until the shared-backlog protocol is released, `enable` refuses.
- **The shims.** `pre-commit`, `commit-msg` and `post-commit` in each clone are the one fixed shim from [Plugin git hooks](#plugin-git-hooks). A hook of the clone's own survives as `<name>.local` and runs first.

`plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh` sets all three up. Init runs both of its parts as its last step. `ralph-init upgrade` runs them once for a project bootstrapped with the legacy copies:

```bash
# Once per project, on one host; review and commit the result, then push
bash <installPath>/skills/ralph-init/scripts/migrate-plugin-hooks.sh tracked [--local-guards <name>[,<name>...]] .
# Once per clone; on a second host, this is the only step after git pull
bash <installPath>/skills/ralph-init/scripts/migrate-plugin-hooks.sh clone .
# Once every clone has run clone: delete the leftover length guard copy, then commit
bash <installPath>/skills/ralph-init/scripts/migrate-plugin-hooks.sh tracked --retire-legacy .
```

- **`tracked`** writes the marker first, so an interrupted run never leaves a guard unenforced. Then it adds the `.gitignore` exception. It removes only the managed guard entries from `.claude/settings.json` and deletes the managed guard copies that are not local guards. It keeps the project's own hooks and entries, and `.claude/hooks/filename-length-guard.sh`, which a legacy pre-commit copy still calls. `--retire-legacy` deletes that copy; it refuses while this clone's pre-commit is not the plugin shim.
- **`clone`** runs on the host only: it refuses with `DEVCONTAINER=true`, because the container shares the host's `.git/config` and would record its own `jq` and `/workspace`. It checks every git hook before it writes anything. It saves the switches and installs the shims, replacing an unedited copy of any hook body ralph-init has ever shipped (`scripts/shipped-git-hooks.sha256`, checked against git history by `tests/python/test_shipped_git_hooks.py`). A differing hook that `.claude/managed-file-drift.accept` lists is kept as `<name>.local`; any other differing hook stops the run, and an existing `<name>.local` is never overwritten. Last, it drops from `.claude/settings.local.json` the common rules your user settings already hold, and reports the ones it kept.

Neither part commits, and a second run changes nothing. After the migration, a plugin update reaches every guard and git hook with no per-project run. The `/ralph-run` preflight reports a project as not migrated, partially migrated, or with shims missing in this clone, and names a leftover `.claude/hooks/filename-length-guard.sh` as removable once this clone's pre-commit is the shim, and `managed-file-drift.sh` stops comparing what the plugin owns. This repo is migrated (TASK-302) but lists all six guards in `localGuards`, so its own guard copies stay wired through `.claude/settings.json` for testing guard changes; its git hooks are the shims, and its pre-push stays a plain hook until the installed plugin on each host carries `git-hooks/pre-push` (TASK-328): moved behind the shim earlier, it fails closed and blocks every push.

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
| `skipped_tasks` | array of objects | Each entry is `{ "task": "TASK-<n>", "iteration": <int> }`: a task that iteration left in To Do. The run does not pick it again and moves on to the next eligible task, in both `--tasks` and default mode. In default and `--prompt-file` mode, where the agent picks its own task, each later prompt names the excluded tasks so the agent does not pick them. The run log and the final summary name each one too |

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

The orchestrator suite lives at `plugins/ralph/skills/ralph-run/tests/test_*.py`, and tests for repo-level scripts live at `tests/python/test_*.py`; both test paths and `pythonpath` are configured in `pyproject.toml`. Run them with uv:

```bash
# Run the full Python suite
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
- Devcontainer, signals, summary, task selection, end-to-end - `test_devcontainer.py`, `test_devcontainer_rebuild.py`, `test_devcontainer_stale.py`, `test_signals.py`, `test_summary.py`, `test_tasks.py`, `test_e2e_fake_claude.py`

**Python (`tests/python/`)** — also run by `uv run pytest`:

- `test_plugin_hooks.py` - Tests the plugin guard hooks: parity of the seven guards with the template and live copies, `hooks.json` against the template `settings.json`, the `run.sh` marker gate (marker present/absent, `localGuards`, subdirectory session, nested repository, input, cwd, `RALPH_PROJECT_ROOT` and exit-code passthrough), the guards' root fallback when run directly, and a template-bootstrapped project still blocking through its legacy wiring
- `test_shorten_backlog_filenames.py` - Tests `scripts/shorten-backlog-filenames.py` (slug normalizer, byte budget math, collision suffixing, backlog-root discovery and per-repo grouping, plus CLI runs over throwaway git repos with a stubbed `claude`: single project, multi-project sweep, pathspec-scoped commits, hook-blocked commits and `--no-verify`)
- `test_devcontainer_*.py` - Pin the devcontainer config on both the live `.devcontainer/` and the ralph-init template: the `.venv` volume overlay, the shared `.claude` scheme and its lifecycle hooks, the host-path `~/.claude` bind, the `CLAUDE_CONFIG_DIR` root, the Claude Code version pin (concrete build arg, no floating `ARG` default, the guard run under `sh`), and the language fragments' Python runtime guard. Each module carries a mutated-copy negative case. `devcontainer_config.py` is their shared JSONC reader (it blanks whole-line `//` comments only; inline comments are not supported)

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
