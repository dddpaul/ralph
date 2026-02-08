# Ralph

![Ralph](ralph.webp)

Ralph is an autonomous AI agent loop that runs AI coding tools ([Amp](https://ampcode.com) or [Claude Code](https://docs.anthropic.com/en/docs/claude-code)) repeatedly until all backlog tasks are complete. Each iteration is a fresh instance with clean context. Memory persists via git history, backlog task notes, and CLAUDE.md/AGENTS.md files.

Based on [Geoffrey Huntley's Ralph pattern](https://ghuntley.com/ralph/) and [Ryan Carson's original Ralph implementation](https://x.com/ryancarson/status/2008548371712135632).

### How this fork differs from the original

The original Ralph uses a single `prd.json` file with `jq` parsing, a shared `progress.txt` for learnings, and one long-lived feature branch per run. This fork replaces all of that with the [Backlog.md CLI](https://github.com/MrLesk/Backlog.md) — each task is a separate file with built-in status, acceptance criteria, and notes. Tasks get per-task branches (`task-<id>-description`) merged to master individually, mandatory code review before every merge, and a `MODE: autonomous` prefix so the same CLAUDE.md works for both the Ralph loop and interactive development.

## Prerequisites

- One of the following AI coding tools installed and authenticated:
  - [Amp CLI](https://ampcode.com) (default)
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`npm install -g @anthropic-ai/claude-code`)
- [Backlog.md CLI](https://github.com/MrLesk/Backlog.md) installed
- A git repository for your project

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
cp -r skills/prd ~/.config/amp/skills/
cp -r skills/ralph ~/.config/amp/skills/
```

For Claude Code
```bash
cp -r skills/prd ~/.claude/skills/
cp -r skills/ralph ~/.claude/skills/
```

### Option 3: Run in DevContainer (sandboxed)

The repository includes a DevContainer with firewall restrictions for sandboxed autonomous agent execution. Network access is limited to approved domains only (GitHub, npm, Anthropic API, etc.).

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
Load the prd skill and create a PRD for [your feature description]
```

Answer the clarifying questions. The skill saves output to `tasks/prd-[feature-name].md`.

### 2. Convert PRD to backlog tasks

Use the Ralph skill to convert the markdown PRD to backlog tasks:

```
Load the ralph skill and convert tasks/prd-[feature-name].md to backlog tasks
```

This creates individual backlog tasks with acceptance criteria, priorities, and dependencies.

### 3. Run Ralph

```bash
# Using Amp (default)
./scripts/ralph/ralph.sh [max_iterations]

# Using Claude Code
./scripts/ralph/ralph.sh --tool claude [max_iterations]

# Run in sandboxed devcontainer
./scripts/ralph/ralph.sh --devcontainer [max_iterations]
```

Default is 10 iterations. Use `--tool amp` or `--tool claude` to select your AI coding tool. Add `--devcontainer` to run in an isolated container with network restrictions.

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

## Dual Mode: Autonomous + Interactive

CLAUDE.md serves both autonomous (Ralph loop) and interactive (human-driven) development:

- **Autonomous mode**: Ralph loop prepends `MODE: autonomous` to the prompt. The agent picks tasks from the backlog and works through them.
- **Interactive mode**: No mode prefix. The agent creates a backlog task for every code change request before implementing.

The same workflow (branch, implement, review, merge) applies in both modes.

## Key Files

| File | Purpose |
|------|---------|
| `ralph.sh` | The bash loop that spawns fresh AI instances (supports `--tool amp\|claude` and `--devcontainer`) |
| `prompt.md` | Prompt template for Amp |
| `CLAUDE.md` | Agent instructions for Claude Code (autonomous + interactive) |
| `backlog/` | Task files managed by backlog.md CLI |
| `.devcontainer/` | DevContainer configuration with firewall for sandboxed execution |
| `skills/prd/` | Skill for generating PRDs |
| `skills/ralph/` | Skill for converting PRDs to backlog tasks |
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

Each iteration spawns a **new AI instance** (Amp or Claude Code) with clean context. The only memory between iterations is:
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

## Customizing

After copying `prompt.md` (for Amp) or `CLAUDE.md` (for Claude Code) to your project, customize it:
- Add project-specific quality check commands
- Include codebase conventions and common gotchas
- Add language/framework instructions to the `## Project-Specific` section at the bottom of CLAUDE.md

## References

- [Geoffrey Huntley's Ralph article](https://ghuntley.com/ralph/)
- [Backlog.md CLI](https://github.com/MrLesk/Backlog.md)
- [Amp documentation](https://ampcode.com/manual)
- [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code)
