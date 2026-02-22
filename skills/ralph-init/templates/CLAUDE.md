# Agent Instructions

## CRITICAL: One Task Per Iteration (Autonomous Mode)

If the prompt starts with `MODE: autonomous`: you MUST complete exactly **ONE** task, then **STOP**. Do NOT pick up another task. The Ralph loop will spawn a fresh instance for the next task. Pick the lowest-ID "To Do" task (or highest priority if set).

After completing the single task, your final output MUST use this exact format:

```
## Task Summary

- **Task:** TASK-<id> — <title>
- **What was implemented:** <description of what was done>
- **Files changed:** <list of files>
- **Key decisions:** <any notable decisions or trade-offs>
```

Then run `backlog task list -s "To Do" --plain`:
- If no "To Do" tasks remain → reply with `<promise>COMPLETE</promise>`
- If tasks remain → end your response (do NOT start another task)

## Workflow

### Task Lifecycle
1. **Create task (if needed):** `backlog task create "Title" -d "Description" --ac "Criterion"` — skip if task already exists
2. **Start work:** `backlog task edit <id> -s "In Progress" -a @claude`
3. **Create branch:** `git checkout -b task-<id>-description master`
4. **Implement:** write code, run build/linter/tests
5. **Check off AC:** `backlog task edit <id> --check-ac <number>`
6. **Commit code:** `git commit -m "task-<id>: message"` (post-commit hook appends hash to task file)
7. **Code review:** spawn Explore agent to review (see below). If changes requested, loop to step 4.
8. **GATE — verify before marking done:** Run build, linter, and tests one final time. ALL must pass. If any fails, loop to step 4. **Never mark a task "Done" with a broken build, failing tests, or linter errors.**
9. **Mark done with notes:** `backlog task edit <id> -s "Done" --append-notes "What was implemented, files changed, learnings"`
10. **Commit task file:** `git add backlog/tasks/task-<id>*.md && git commit -m "task-<id>: Update task file"`
11. **Merge and clean up:** `git checkout master && git merge <branch> && git branch -d <branch>`
12. **Output summary:** Print the `## Task Summary` block defined at the top of this file with all fields filled in.

### Git Hooks
The post-commit hook appends commit hash to task files on `task-*` branches. The task file stays uncommitted to preserve the exact hash. On amends, it updates the hash.

**Never use `--notes`** — it overwrites the Notes section, destroying commit hashes. Use `--append-notes` instead.

### Backlog CLI Reference
Use `backlog` CLI for all task operations. **Never edit task files directly.**
- `backlog task list --plain` / `backlog task <id> --plain`
- `backlog task create "Title" -d "Description" --ac "Criterion"`
- `backlog task edit <id> -s "In Progress" -a @claude`
- `backlog task edit <id> --check-ac 1`

For complex task management — breakdowns, AC writing, quality review — use the `project-manager-backlog` agent. It enforces task atomicity, outcome-oriented acceptance criteria, and proper dependency ordering.

### Project Knowledge Sources
When exploring or researching this codebase, check available documentation:
- `README.md` and `*.md` files in repo root and subdirectories
- Run `backlog doc list --plain` to check for backlog docs (may not exist). If present, read relevant ones with `backlog doc view <id>`
- `CLAUDE.md` / `AGENTS.md` files for agent-specific conventions

## Rules

### Code Quality
- Always run build, linter, and tests before committing
- Run tests after significant changes to verify functionality
- Do NOT commit broken code
- Follow existing code patterns
- **CRITICAL: A task may ONLY be marked "Done" if ALL of the following pass: (1) build succeeds, (2) all tests pass, (3) linter reports zero errors, (4) code review is approved.** If any of these fail, the task MUST remain "In Progress" until all issues are resolved. No exceptions.

### Commit & PR Brevity
- Commit messages must not describe changes, progress, or historical modifications
- Avoid commit messages like "new function," "added test," "now we changed this," or "previously used X, now using Y"
- Do not add "Generated with Claude Code" or "Co-Authored-By" trailers to commits or PRs
- Do not add "Test plan" sections in PR descriptions
- Commit messages should describe what the code does, not its history or evolution

### Scope
- **MANDATORY: A backlog task MUST exist BEFORE writing any code.** When asked to implement a feature or fix in interactive mode, first create a task with `backlog task create`, then follow the Task Lifecycle. No exceptions.
- Do not execute tasks you were not asked to do
- One task per iteration, one branch per task
- Keep changes focused and minimal
- Always merge to master and delete task branch when done

### Knowledge Sharing
- Update README.md after adding important functionality
- Update nearby CLAUDE.md files with reusable patterns (API conventions, gotchas, dependencies — not task-specific details)
- Add implementation notes to completed tasks via `--append-notes`

## Code Review

**Every task branch MUST be reviewed before merging.** No exceptions.

After tests pass, spawn an Explore agent:
```
Review changes in branch task-<id> for merge to master.
Run: git diff master..HEAD
Check requirements: backlog task <id> --plain
```

**Checklist:**
1. Acceptance criteria met
2. Functionality correct, edge cases handled
3. No bugs, proper error handling
4. No security issues (injection, XSS, secrets)
5. Consistent code style
6. Test coverage for new functionality
7. No debug code or commented-out code
8. No unintended changes to other files

Only merge after reviewer approval. If changes requested, fix and re-review.

## Browser Testing

For UI tasks, verify in browser if tools are available (e.g., MCP). Note in task if manual verification is needed.

## Project-Specific

- **Language:** <FILL IN from user's answer to Q1>
- **Build:** `<FILL IN from user's answer to Q2>`
- **Lint:** `<FILL IN from user's answer to Q2>`
- **Test:** `<FILL IN from user's answer to Q2>`
- **Framework:** <FILL IN if mentioned>

### Conventions
<!-- Add project conventions here -->
