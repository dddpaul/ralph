# Ralph Agent Instructions

You are an autonomous coding agent working on a software project.

## Your Task

1. List pending tasks: `backlog task list -s "To Do" --plain`
2. Pick the next task:
   - Default: lowest task ID
   - If priorities exist: highest priority first
3. Read task details: `backlog task <id> --plain`
4. Follow the Full Task Workflow below to implement, review, and merge

## Important Workflow Notes
- **MANDATORY: Make sure there is backlog task BEFORE writing any code.** When asked to implement a feature or fix, first create a task with `backlog task create`, set it in progress, assign to @claude, and create a task branch. Only then start coding. No exceptions.
- Do not execute any tasks that not being asked to do
- Always run build, tests, linter before committing
- Do NOT commit broken code
- Run tests and linter after making significant changes to verify functionality
- Don't add "Generated with Claude Code" or "Co-Authored-By: Claude" to commit messages or PRs
- Do not include "Test plan" sections in PR descriptions
- Do not add comments that describe changes, progress, or historical modifications. Avoid comments like "new function," "added test," "now we changed this," or "previously used X, now using Y." Comments should only describe the current state and purpose of the code, not its history or evolution.
- After important functionality added, update README.md accordingly
- Work on ONE task per iteration
- Each task gets its own branch: `task-<id>-<short-description>`
- Always merge to master before finishing
- Delete task branch after merge

## Git Flow with Backlog Hooks
The post-commit hook automatically appends commit hash to task files when on a `task-XXX-*` branch. The task file stays uncommitted to preserve the exact hash. On amends, it updates the hash.

**Never use `--notes` flag** — it overwrites the entire Notes section, destroying commit hashes appended by the hook. Always use `--append-notes` instead.

### Full Task Workflow
1. **Create task:** `backlog task create "Title" -d "Description" --ac "Criterion"`
2. **Start work:** `backlog task edit <id> -s "In Progress" -a @claude`
3. **Create branch:** `git checkout -b task-XXX-description`
4. **Implement:** write code, run linter, run tests
5. **Commit code:** `git commit -m "task-XXX: message"` (hook appends hash to task file)
6. **Code review:** spawn Explore agent to review changes (see below). If changes requested, loop back to step 4.
7. **Mark done:** `backlog task edit <id> -s "Done"`
8. **Commit task file:** `git add backlog/tasks/task-XXX*.md && git commit -m "Update task file"`
9. **Merge and clean up:** `git checkout master && git merge <branch> && git branch -d <branch>`

## Mandatory Code Review Before Merge

**Every task branch MUST be reviewed before merging to master.** No exceptions.

After implementation is complete and tests pass, spawn an Explore agent to review the changes:

```
Review the changes in branch task-XXX for merge to master.
Run: git diff master..HEAD
Check the task requirements: backlog task XXX --plain
```

**Review Checklist:**
1. **Acceptance Criteria** - All AC items are implemented and verified
2. **Functionality** - Code does what it's supposed to do, edge cases handled
3. **Bugs** - No obvious bugs, null checks, error handling present
4. **Security** - No SQL injection, XSS, command injection, secrets in code
5. **Code Style** - Consistent with project conventions, readable
6. **Tests** - New functionality has appropriate test coverage
7. **No Debug Code** - No console.log, print statements, commented code left behind
8. **Unintended Changes** - No accidental modifications to unrelated files

**Review Outcomes:**
- Approved - Proceed with merge
- Changes Requested - Fix issues and re-review
- Rejected - Significant problems, needs rework

Only merge after receiving explicit approval from the reviewer.

## Task Management with Backlog CLI

Use `backlog` CLI for all task operations. **Never edit task files directly.**

Key commands:
- `backlog task create "Title" -d "Description" --ac "Criterion"`
- `backlog task edit <id> -s "In Progress" -a @claude`
- `backlog task edit <id> --check-ac 1`
- `backlog task list --plain` / `backlog task <id> --plain`

## Implementation Notes Format

Add notes to the completed task (via `--notes` flag):
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered (e.g., "this codebase uses X for Y")
  - Gotchas encountered (e.g., "don't forget to update Z when changing W")
  - Useful context (e.g., "the evaluation panel is in component X")

The learnings section is critical - it helps future iterations avoid repeating mistakes and understand the codebase better.

## Update CLAUDE.md Files

Before committing, check if any edited files have learnings worth preserving in nearby CLAUDE.md files:

1. **Identify directories with edited files** - Look at which directories you modified
2. **Check for existing CLAUDE.md** - Look for CLAUDE.md in those directories or parent directories
3. **Add valuable learnings** - If you discovered something future developers/agents should know:
   - API patterns or conventions specific to that module
   - Gotchas or non-obvious requirements
   - Dependencies between files
   - Testing approaches for that area
   - Configuration or environment requirements

**Examples of good CLAUDE.md additions:**
- "When modifying X, also update Y to keep them in sync"
- "This module uses pattern Z for all API calls"
- "Tests require the dev server running on PORT 3000"
- "Field names must match the template exactly"

**Do NOT add:**
- Task-specific implementation details
- Temporary debugging notes
- Information already in task notes

Only update CLAUDE.md if you have **genuinely reusable knowledge** that would help future work in that directory.

## Browser Testing (If Available)

For any task that changes UI, verify it works in the browser if you have browser testing tools configured (e.g., via MCP):

1. Navigate to the relevant page
2. Verify the UI changes work as expected
3. Take a screenshot if helpful for the task notes

If no browser tools are available, note in the task notes that manual browser verification is needed.

## Stop Condition

After completing a task:
1. Run: `backlog task list -s "To Do" --plain`
2. If NO tasks remain with status "To Do": reply with <promise>COMPLETE</promise>
3. If tasks remain: end normally (next iteration picks up)

