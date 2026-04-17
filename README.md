# Ralph

![Ralph](ralph.webp)

Ralph is an autonomous AI agent loop that runs AI coding tools ([Amp](https://ampcode.com), [Claude Code](https://docs.anthropic.com/en/docs/claude-code), or [opencode](https://opencode.ai)) repeatedly until all backlog tasks are complete. Each iteration is a fresh instance with clean context. Memory persists via git history, backlog task notes, and CLAUDE.md/AGENTS.md files.

Based on [Geoffrey Huntley's Ralph pattern](https://ghuntley.com/ralph/) and [Ryan Carson's original Ralph implementation](https://x.com/ryancarson/status/2008548371712135632).

### How this fork differs from the original

The original Ralph uses a single `prd.json` file with `jq` parsing, a shared `progress.txt` for learnings, and one long-lived feature branch per run. This fork replaces all of that with the [Backlog.md CLI](https://github.com/MrLesk/Backlog.md) — each task is a separate file with built-in status, acceptance criteria, and notes. Tasks get per-task branches (`task-<id>-description`) merged to main individually, mandatory code review before every merge, and a `MODE: autonomous` prefix so the same CLAUDE.md works for both the Ralph loop and interactive development.

## Prerequisites

- One of the following AI coding tools installed and authenticated:
  - [Amp CLI](https://ampcode.com) (default)
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`npm install -g @anthropic-ai/claude-code`)
  - [opencode](https://opencode.ai) (`npm install -g @opencode/cli`)
- [Backlog.md CLI](https://github.com/MrLesk/Backlog.md) installed
- A git repository for your project
- For running tests: [bats-core](https://github.com/bats-core/bats-core) (`npm install` or see [bats-core installation](https://github.com/bats-core/bats-core#installation))

## Setup

### Option 1: Copy to your project

Copy the ralph files into your project:

```bash
# From your project root
mkdir -p scripts/ralph
cp /path/to/ralph/ralph.sh scripts/ralph/

# Copy the prompt template for your AI tool of choice:
cp /path/to/ralph/prompt.md scripts/ralph/prompt.md    # For Amp
# OR
cp /path/to/ralph/CLAUDE.md scripts/ralph/CLAUDE.md    # For Claude Code

chmod +x scripts/ralph/ralph.sh
```

### Option 2: Install skills globally

Copy the skills to your Amp or Claude config for use across all projects:

For AMP
```bash
cp -r skills/ralph-init ~/.config/amp/skills/
cp -r skills/ralph-prd ~/.config/amp/skills/
cp -r skills/ralph-backlog ~/.config/amp/skills/
```

For Claude Code
```bash
cp -r skills/ralph-init ~/.claude/skills/
cp -r skills/ralph-prd ~/.claude/skills/
cp -r skills/ralph-backlog ~/.claude/skills/
```

For opencode
```bash
cp -r skills/ralph-init ~/.opencode/skills/
cp -r skills/ralph-prd ~/.opencode/skills/
cp -r skills/ralph-backlog ~/.opencode/skills/
```

### Option 3: Run in DevContainer (sandboxed)

The repository includes a DevContainer with firewall restrictions for sandboxed autonomous agent execution. Network access is limited to approved domains only (GitHub, npm, Anthropic API, etc.).

**Runtime:** The default Dockerfile includes Go 1.25, but you can replace Stage 1 with any language runtime (Python, Ruby, Java, etc.) by modifying `.devcontainer/Dockerfile`.

To run Ralph in the devcontainer:

```bash
./ralph.sh --devcontainer [max_iterations]
```

This starts the container automatically and executes Ralph inside the isolated environment. The firewall (`init-firewall.sh`) restricts outbound network access using iptables and validates restrictions on startup.

### Configure Amp auto-handoff (recommended)

Add to `~/.config/amp/settings.json`:

```json
{
  "amp.experimental.autoHandoff": { "context": 90 }
}
```

This enables automatic handoff when context fills up, allowing Ralph to handle large tasks that exceed a single context window.

## Workflow

### 1. Create a PRD

Use the PRD skill to generate a detailed requirements document:

```
Load the ralph-prd skill and create a PRD for [your feature description]
```

Answer the clarifying questions. The skill saves output to `tasks/prd-[feature-name].md`.

### 2. Convert PRD to backlog tasks

Use the Ralph backlog skill to convert the markdown PRD to backlog tasks:

```
Load the ralph-backlog skill and convert tasks/prd-[feature-name].md to backlog tasks
```

This creates individual backlog tasks with acceptance criteria, priorities, and dependencies.

### 3. Run Ralph

```bash
# Using Amp (default)
./scripts/ralph/ralph.sh [max_iterations]

# Using Claude Code
./scripts/ralph/ralph.sh --tool claude [max_iterations]

# Using Claude Code with low effort (faster, cheaper)
./scripts/ralph/ralph.sh --tool claude --effort low [max_iterations]

# Using opencode
./scripts/ralph/ralph.sh --tool opencode [max_iterations]

# Run in sandboxed devcontainer
./scripts/ralph/ralph.sh --devcontainer [max_iterations]

# With error handling options
./scripts/ralph/ralph.sh --on-error retry --retry-count 3 --log-file ralph.log
```

Default is 10 iterations. Use `--tool amp`, `--tool claude`, or `--tool opencode` to select your AI coding tool. Add `--devcontainer` to run in an isolated container with network restrictions.

### Error Handling Options

Ralph supports configurable error handling for AI tool failures:

| Option | Description | Default |
|--------|-------------|---------|
| `--effort <level>` | Thinking effort for Claude Code: `low`, `medium`, `high`, or `max` | `medium` |
| `--on-error <strategy>` | How to handle AI tool errors: `stop`, `continue`, or `retry` | `stop` |
| `--retry-count <n>` | Number of retries when `--on-error=retry` | `2` |
| `--log-file <path>` | Log errors to file for later analysis | (none) |

**Strategies:**

- **stop** (default): Immediately exit on any error. Best for production runs where you want to investigate failures manually.
- **continue**: Log the error and proceed to the next iteration. Useful for long overnight runs where you want to maximize progress.
- **retry**: Retry failed iterations up to N times before giving up. Good for transient network issues or rate limits.

**Examples:**

```bash
# Stop immediately on error (default behavior)
./ralph.sh --tool opencode

# Continue to next iteration on error, log to file
./ralph.sh --on-error continue --log-file errors.log

# Retry failed iterations up to 3 times
./ralph.sh --on-error retry --retry-count 3
```

Ralph will:
1. Check for remaining "To Do" tasks via `backlog task list`
2. Pick the next task (lowest ID or highest priority)
3. Create a branch (`task-<id>-description`) from main
4. Implement the task
5. Run quality checks (build, lint, tests)
6. Commit code, then run mandatory code review
7. Mark task as "Done", commit task file
8. Merge to main and delete the task branch
9. Repeat until all tasks are done or max iterations reached

Each iteration gets a `MODE: autonomous` prefix so the agent knows it's running in the Ralph loop vs interactive mode.

## Dual Mode: Autonomous + Interactive

CLAUDE.md serves both autonomous (Ralph loop) and interactive (human-driven) development:

- **Autonomous mode**: Ralph loop prepends `MODE: autonomous` to the prompt. The agent picks tasks from the backlog and works through them.
- **Interactive mode**: No mode prefix. The agent creates a backlog task for every code change request before implementing.

The same workflow (branch, implement, review, merge) applies in both modes.

## Key Files

| File | Purpose |
|------|---------|
| `ralph.sh` | The bash loop that spawns fresh AI instances (supports `--tool amp\|claude\|opencode` and `--devcontainer`) |
| `prompt.md` | Prompt template for Amp |
| `CLAUDE.md` | Agent instructions for Claude Code (autonomous + interactive) |
| `backlog/` | Task files managed by backlog.md CLI |
| `.devcontainer/` | DevContainer configuration with firewall for sandboxed execution |
| `skills/ralph-init/` | Skill for bootstrapping Ralph in a new project |
| `skills/ralph-prd/` | Skill for generating PRDs |
| `skills/ralph-backlog/` | Skill for converting PRDs to backlog tasks |
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

Each iteration spawns a **new AI instance** (Amp, Claude Code, or opencode) with clean context. The only memory between iterations is:
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

Each task gets its own branch (`task-<id>-description`) created from main. After the task is complete, code review passes, and quality checks pass, the branch is merged back to main and deleted. This keeps main always up-to-date and avoids long-lived feature branches.

### Mandatory Code Review

Every task branch is reviewed before merging. The agent spawns an Explore agent to check acceptance criteria, functionality, security, code style, and test coverage. Only approved branches get merged.

### Git Hooks

The post-commit hook appends commit hashes to task files on `task-*` branches. This creates an audit trail linking commits to tasks. Use `--append-notes` (never `--notes`) to avoid overwriting hook-generated content.

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

Ralph uses [bats-core](https://github.com/bats-core/bats-core) for bash script testing. Tests verify argument validation, dependency checks, prompt generation, timeout handling, completion signals, and end-to-end workflows.

### Install bats-core

**Option 1: npm (recommended)**

```bash
npm install
```

**Option 2: System-wide installation**

See [bats-core installation guide](https://github.com/bats-core/bats-core#installation) for your platform.

### Run tests

```bash
# Run all tests
npm test

# Run unit tests only
npm run test:unit

# Run integration tests only
npm run test:integration

# Run E2E tests
npm run test:e2e
```

### Test structure

- `tests/unit/` - Unit tests for individual functions (argument validation, dependency checks)
- `tests/integration/` - Integration tests for component interactions (prompt generation, timeout handling, completion signal)
- `tests/e2e/` - End-to-end tests for full workflows with real backlog tasks
- `tests/helpers/` - Shared test utilities and mocks (`common.bash`)

### Test files

- `argument-validation.bats` - Validates CLI arguments (--tool, --devcontainer, max_iterations)
- `dependency-checks.bats` - Tests dependency verification (git, backlog CLI, AI tools)
- `prompt-generation.bats` - Tests prompt template loading and MODE: autonomous prefix injection
- `timeout-handling.bats` - Tests iteration timeout and graceful shutdown
- `completion-signal.bats` - Tests <promise>COMPLETE</promise> detection and loop termination

## Customizing

After copying `prompt.md` (for Amp) or `CLAUDE.md` (for Claude Code/opencode) to your project, customize it:
- Add project-specific quality check commands
- Include codebase conventions and common gotchas
- Add language/framework instructions to the `## Project-Specific` section at the bottom of CLAUDE.md

## References

- [Geoffrey Huntley's Ralph article](https://ghuntley.com/ralph/)
- [Backlog.md CLI](https://github.com/MrLesk/Backlog.md)
- [Amp documentation](https://ampcode.com/manual)
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

If a task branch has conflicts with main:
1. Rebase onto main: `git rebase main`
2. Resolve conflicts
3. Continue: `git rebase --continue`
4. Run tests to verify the fix

**Tests timing out**

Increase timeout values in test files if needed, or check for hanging processes. E2E tests may take longer on slower systems.
