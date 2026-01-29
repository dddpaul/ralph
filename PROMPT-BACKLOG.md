# Migration Proposal: Ralph from prd.json to Backlog.md CLI

## Summary

Replace Ralph's single `prd.json` file with the [Backlog.md CLI](https://github.com/MrLesk/Backlog.md) tool. Each task becomes its own branch (`task-<id>`), gets merged to main after completion, and Ralph loops through all tasks.

## Motivation

The current `prd.json` approach has limitations:
- Single monolithic file for all tasks
- Requires `jq` for parsing
- Manual archiving needed between runs
- Progress tracking split between `prd.json` and `progress.txt`

The backlog.md CLI provides:
- Individual task files with rich metadata
- Built-in status management (`To Do` / `In Progress` / `Done`)
- Acceptance criteria, priorities, and dependencies as first-class features
- Notes attached directly to tasks (replacing `progress.txt`)

## New Workflow

```
1. backlog task list -s "To Do" --plain  →  pick next task (lowest ID or highest priority)
2. git checkout -b task-<id> main
3. backlog task edit <id> -s "In Progress"
4. View task details: backlog task <id> --plain
5. Implement the task
6. Run quality checks
7. Commit: feat: task-<id> - <title>
8. git checkout main && git merge task-<id>
9. backlog task edit <id> -s "Done" --notes "Implementation notes..."
10. Check remaining tasks → loop or output <promise>COMPLETE</promise>
```

## Key Mappings

| prd.json | backlog.md |
|----------|------------|
| `passes: false` | Status: "To Do" |
| `passes: true` | Status: "Done" |
| `priority: 1,2,3` | Task ID order (or `--priority` flag) |
| `branchName` | Derived: `task-<id>` |
| `acceptanceCriteria[]` | `--ac` flag / `## Acceptance Criteria` |
| `progress.txt` learnings | `--notes` on the task |

## Changes Made

### `ralph.sh` — Core loop rewrite
- Removed: `PRD_FILE` / `jq` parsing, `PROGRESS_FILE`, `.last-branch` tracking, archive logic
- Added: backlog CLI availability check, task discovery via `backlog task list`, remaining task count display

### `CLAUDE.md` — Full rewrite for backlog workflow
- Replaced prd.json steps with backlog CLI commands
- Progress reporting via `--notes` flag instead of `progress.txt`
- Stop condition checks `backlog task list -s "To Do"` instead of `passes: true`

### `prompt.md` — Same changes as CLAUDE.md (for Amp)
- Mirrors CLAUDE.md changes with Amp-specific differences (thread URL, AGENTS.md vs CLAUDE.md, dev-browser skill requirement)

### `skills/ralph/SKILL.md` — Backlog task output
- Replaced JSON output format with `backlog task create` commands
- Added `--dep task-<id>` dependency syntax
- Updated example to use CLI commands

### `skills/prd/SKILL.md` — Next step note
- Added "Next Step" section pointing to ralph skill for backlog task creation

### `README.md` — Full documentation update
- Replaced `prd.json` references with backlog.md CLI
- Updated workflow section, key files table, debugging commands
- Removed archiving section (per-task branches eliminate the need)
- Added per-task branching explanation

### `AGENTS.md` — Updated references
- Replaced `prd.json` / `prd.json.example` references with `backlog/`
- Updated memory persistence description

### Deleted: `prd.json.example`
- No longer needed — backlog.md format replaces it

## Branch Strategy

- **Per-task branching**: Each task gets `task-<id>` branch from main
- **Merge after each task**: No long-lived feature branches
- **Main always current**: Each merge brings main up to date

## Task Ordering

- Default: lowest task ID first (tasks created in dependency order)
- Override: `--priority` flag on tasks for explicit ordering
- Dependencies: `--dep task-<id>` prevents starting blocked tasks
