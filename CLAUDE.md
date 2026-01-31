# Ralph Agent Instructions

You are an autonomous coding agent working on a software project.

## Your Task

1. List pending tasks: `backlog task list -s "To Do" --plain`
2. Pick the next task:
   - Default: lowest task ID
   - If priorities exist: highest priority first
3. Read task details: `backlog task <id> --plain`
4. Create branch: `git checkout -b task-<id> master`
5. Mark in progress: `backlog task edit <id> -s "In Progress"`
6. Implement the task
7. Run quality checks (typecheck, lint, test - use whatever your project requires)
8. Update CLAUDE.md files if you discover reusable patterns (see below)
9. If checks pass, commit ALL changes with message: `feat: task-<id> - <title>`
10. Merge to master: `git checkout master && git merge task-<id>`
11. Mark done: `backlog task edit <id> -s "Done"`
12. Add implementation notes: `backlog task edit <id> --notes "..."`

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

## Quality Requirements

- ALL commits must pass your project's quality checks (typecheck, lint, test)
- Do NOT commit broken code
- Keep changes focused and minimal
- Follow existing code patterns

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

## Important

- Work on ONE task per iteration
- Each task gets its own branch: `task-<id>`
- Always merge to master before finishing
- Use `--plain` flag for all backlog CLI output
- Commit frequently
- Keep CI green
