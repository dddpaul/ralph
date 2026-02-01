# Agent Instructions

## Workflow

### Task Lifecycle
1. **Create task (if needed):** `backlog task create "Title" -d "Description" --ac "Criterion"` — skip if task already exists
2. **Start work:** `backlog task edit <id> -s "In Progress" -a @claude`
3. **Create branch:** `git checkout -b task-<id>-description master`
4. **Implement:** write code, run build/linter/tests
5. **Check off AC:** `backlog task edit <id> --check-ac <number>`
6. **Commit code:** `git commit -m "task-<id>: message"` (post-commit hook appends hash to task file)
7. **Code review:** spawn Explore agent to review (see below). If changes requested, loop to step 4.
8. **Mark done:** `backlog task edit <id> -s "Done"`
9. **Commit task file:** `git add backlog/tasks/task-<id>*.md && git commit -m "Update task file"`
10. **Merge and clean up:** `git checkout master && git merge <branch> && git branch -d <branch>`

### Git Hooks
The post-commit hook appends commit hash to task files on `task-*` branches. The task file stays uncommitted to preserve the exact hash. On amends, it updates the hash.

**Never use `--notes`** — it overwrites the Notes section, destroying commit hashes. Use `--append-notes` instead.

### Backlog CLI Reference
Use `backlog` CLI for all task operations. **Never edit task files directly.**
- `backlog task list --plain` / `backlog task <id> --plain`
- `backlog task create "Title" -d "Description" --ac "Criterion"`
- `backlog task edit <id> -s "In Progress" -a @claude`
- `backlog task edit <id> --check-ac 1`

## Rules

### Code Quality
- Always run build, linter, and tests before committing
- Run tests after significant changes to verify functionality
- Do NOT commit broken code
- Follow existing code patterns

### Commit Hygiene
- No "Generated with Claude Code" or "Co-Authored-By" in commits or PRs
- No "Test plan" sections in PR descriptions
- No historical comments ("added X", "changed Y to Z") — comments describe current state only

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

## Ralph Loop (Autonomous Mode)

Activated when the prompt starts with `MODE: autonomous`. When in this mode:

1. Pick next task: `backlog task list -s "To Do" --plain` (lowest ID, or highest priority)
2. Read details: `backlog task <id> --plain`
3. Execute the Task Lifecycle above
4. After completing: if no "To Do" tasks remain, reply with `<promise>COMPLETE</promise>`. Otherwise end normally.

## Browser Testing

For UI tasks, verify in browser if tools are available (e.g., MCP). Note in task if manual verification is needed.

## Project-Specific

<!-- Add language, framework, and tech stack instructions below -->
