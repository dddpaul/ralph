# Ralph Agent Instructions

## Overview

Ralph is an autonomous AI agent loop that runs AI coding tools (Amp, Claude Code, or opencode) repeatedly until all backlog tasks are complete. Each iteration is a fresh instance with clean context.

## Commands

```bash
# Run the flowchart dev server
cd flowchart && npm run dev

# Build the flowchart
cd flowchart && npm run build

# Run Ralph with Amp (default)
./ralph.sh [max_iterations]

# Run Ralph with Claude Code
./ralph.sh --tool claude [max_iterations]

# Run Ralph with opencode
./ralph.sh --tool opencode [max_iterations]

# Check task status
backlog task list --plain
```

## Key Files

- `ralph.sh` - The bash loop that spawns fresh AI instances (supports `--tool amp`, `--tool claude`, or `--tool opencode`)
- `prompt.md` - Instructions given to each AMP instance
- `CLAUDE.md` - Instructions given to each Claude Code instance
- `backlog/` - Task files managed by backlog.md CLI
- `skills/ralph-init/` - Skill for bootstrapping Ralph in a new project
- `skills/ralph-prd/` - Skill for generating PRDs
- `skills/ralph-backlog/` - Skill for converting PRDs to backlog tasks
- `flowchart/` - Interactive React Flow diagram explaining how Ralph works

## Flowchart

The `flowchart/` directory contains an interactive visualization built with React Flow. It's designed for presentations - click through to reveal each step with animations.

To run locally:
```bash
cd flowchart
npm install
npm run dev
```

## Patterns

- Each iteration spawns a fresh AI instance (Amp, Claude Code, or opencode) with clean context
- Memory persists via git history, backlog task notes, and CLAUDE.md/AGENTS.md files
- Tasks should be small enough to complete in one context window
- Each task gets its own branch (`task-<id>`) merged to main after completion
- Always update AGENTS.md with discovered patterns for future iterations

## Testing

Ralph uses bats-core for bash script testing. Run tests before marking tasks complete.

```bash
# Run all tests
npm test

# Run specific test suites
npm run test:unit
npm run test:integration
npm run test:e2e
```

Test structure:
- `tests/unit/` - Unit tests for argument validation, dependency checks
- `tests/integration/` - Integration tests for prompt generation, timeout handling, completion signal
- `tests/e2e/` - End-to-end tests for full workflows
- `tests/helpers/common.bash` - Shared test utilities and mocks
