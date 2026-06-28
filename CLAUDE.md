# Agent Instructions

## Autonomous Mode

If the prompt starts with `MODE: autonomous`: complete exactly **ONE** task, then **STOP**. The Ralph loop spawns a fresh instance for the next task.

Task selection: if the prompt names a task, work on that task only. Otherwise, run `backlog task list -s "To Do" --plain` and pick the lowest-ID task whose dependencies are all "Done".

After completing the task, output:

```
## Task Summary

- **Task:** TASK-<id> — <title>
- **What was implemented:** <description of what was done>
- **Files changed:** <list of files>
- **Key decisions:** <any notable decisions or trade-offs>
```

Then run `backlog task list -s "To Do" --plain`: if none remain → reply `<promise>COMPLETE</promise>`; if tasks remain → end your response.

## Task Lifecycle

1. **Gate:** verify a backlog task exists and is "In Progress" — create or update status first.
2. **Plan:** read task, AC, and relevant code. Record plan: `backlog task edit <id> --append-notes "Plan: ..."`.
3. **Implement:** write code, run build/linter/tests, check off AC with `backlog task edit <id> --check-ac <n>`.
4. **Review:** after tests pass, spawn the `task-reviewer` agent (NOT `general-purpose` or any other) on `git diff master..HEAD`. Do not proceed to step 5 (Done) or step 6 (Merge) without an APPROVED verdict from the task-reviewer agent.
5. **Done:** final build+lint+tests must pass. `backlog task edit <id> -s "Done" --append-notes "..."`.
6. **Merge:** commit task file, `git checkout master && git merge <branch> && git branch -d <branch>`.

Use `backlog` CLI for all task operations; run `backlog task edit --help` for syntax. For one-off / ad-hoc task creation and judgment-bearing edits (split / add as AC / rework vague AC), use the `ralph-task` skill ("create a task" / "add a task" / "should I split this"). For PRD-driven feature decomposition, use `ralph-prd` then `ralph-backlog`.

Prefer `backlog task edit` for: adding/removing acceptance criteria, status changes, dependency edits, label/priority changes, frontmatter changes, append-notes, and AC checkbox flips (`--check-ac` / `--uncheck-ac`). Direct Edit tool is acceptable for in-place text changes inside the description body or inside an existing AC's text — any change whose diff stays within an existing line and does not touch frontmatter, section markers (`<!-- SECTION:... -->`, `<!-- AC:... -->`), or the count of AC lines.

### Project Knowledge Sources
- `README.md` and `*.md` files in repo root and subdirectories
- Run `backlog doc list --plain` to check for backlog docs (may not exist). If present, read relevant ones with `backlog doc view <id>`
- `CLAUDE.md` / `AGENTS.md` files for agent-specific conventions

## Rules

### Code Quality
- Always run build, linter, and tests before committing
- Run tests after significant changes to verify functionality
- Do NOT commit broken code
- Follow existing code patterns
- **A task may ONLY be marked "Done" if build, tests, linter, and code review ALL pass.**

### Commit & PR Brevity
Commit messages should describe what the code does, not its history or evolution.

### Scope
Every change needs a backlog task and a `task-*` branch — the master-branch hook enforces this. One task per iteration, one branch per task. Keep changes focused and minimal.

### Knowledge Sharing
- Update README.md after adding important functionality
- Update nearby CLAUDE.md files with reusable patterns (API conventions, gotchas, dependencies — not task-specific details)
- Add implementation notes to completed tasks via `--append-notes`

## Browser Testing

For UI tasks, verify in browser if tools are available (e.g., MCP). Note in task if manual verification is needed.

## Handoff Inbox

Some tasks in this project's backlog are inbound handoffs from another Ralph project (created via `/ralph-handoff` in the source). They carry a `Source: <abs-path>@<sha>` line in the description and a "Before starting" validation checklist.

When the user types something like `check new task TASK-NNN — do you understand, can you run it?`, treat it as a handoff acceptance gate:

1. Read the task body in full (`backlog task view <id> --plain`).
2. Run the task's "Before starting" checklist literally:
   - Verify every `(exists)` file path in the Files section is present on disk in this repo.
   - Confirm each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
   - Confirm all dependencies listed in the task's frontmatter are status=Done.
   - Confirm out-of-scope items will not be accidentally pulled in.
3. Report green / yellow / red:
   - **green** — all checks pass, AC is testable, paths exist. You can run it. Reply with a one-paragraph restatement of what you would do, then wait for the user to say "go".
   - **yellow** — one or two ambiguities. List them and ask the user to clarify before starting.
   - **red** — multiple checks fail (paths missing, AC untestable, deps unmet). STOP. Report the failures and ask the user to either fix the task or rescind the handoff.
4. Do NOT start work until the user confirms after a green or clarified-yellow report.

This gate applies even if autonomous mode is otherwise active — a Source-carrying task pulled by the autonomous selector must run the checklist first and stop on red.

## Project-Specific

- **Language:** Python (orchestrator) + Bash (hooks, git hooks, sync, firewall) + Markdown (skills, agents, docs)
- **Build:** `N/A`
- **Lint:** `uv run ruff check .` (Python); shell scripts must satisfy R5 GNU/BSD portability per `.claude/task-reviewer-rules.md`
- **Test:** `uv run pytest`
- **Framework:** Ralph workflow repo — autonomous Claude Code loop (`ralph.sh`) over Backlog.md tasks, with skills under `skills/<name>/` and agents under `agents/<name>.md`.
- **Skill layout:** skills live at `skills/<name>/SKILL.md` (e.g., `skills/ralph-run/SKILL.md`); agents at `agents/<name>.md`. The `ralph-sync` skill propagates `skills/` and `agents/` to `~/.claude/skills/` and `~/.claude/agents/` so they are reachable from any project. R11 (`.claude/task-reviewer-rules.md`) additionally requires template parity between live `.claude/` files and `skills/ralph-init/templates/` for the bootstrap content. This repo is NOT a Claude Code plugin marketplace — there is no `.claude-plugin/marketplace.json` or `plugin.json`.

### Conventions

Use uv exclusively for Python package management in this project.

**Package Management Commands**

- All Python dependencies **must be installed, synchronized, and locked** using uv
- Never use pip, pip-tools, poetry, or conda directly for dependency management

Use these commands:

- Install dependencies: `uv add <package>`
- Remove dependencies: `uv remove <package>`
- Sync dependencies: `uv sync`

**Running Python Code**

- Run a Python script with `uv run <script-name>.py`
- Run Python tools like Pytest with `uv run pytest` or `uv run ruff`
- Launch a Python repl with `uv run python`
- Run test with `uv run pytest <test-name>.py`

**Managing Scripts with PEP 723 Inline Metadata**

- Run a Python script with inline metadata (dependencies defined at the top of the file) with: `uv run script.py`
- You can add or remove dependencies manually from the `dependencies =` section at the top of the script, or
- Or using uv CLI:
    - `uv add package-name --script script.py`
    - `uv remove package-name --script script.py`

### Code Style

- Formatting: Follow PEP 8, use ruff formatter
- Imports: Sort imports with standard library first, then third-party, then local
- Types: Use type hints for all functions and methods
- Naming: snake_case for functions/variables, PascalCase for classes
- Error handling: Use specific exceptions, include context in error messages
- Docstrings: Google-style docstrings for public functions/classes
- Line length: Maximum 88 characters
- Function length: Keep functions focused and under 50 lines
