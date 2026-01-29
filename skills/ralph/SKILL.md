---
name: ralph
description: "Convert PRDs to backlog tasks for the Ralph autonomous agent system. Use when you have an existing PRD and need to create backlog tasks from it. Triggers on: convert this prd, turn this into ralph format, create backlog tasks from this, ralph tasks."
---

# Ralph Backlog Task Creator

Converts existing PRDs to backlog tasks that Ralph uses for autonomous execution.

---

## The Job

Take a PRD (markdown file or text) and create backlog tasks using the `backlog` CLI.

---

## Output Format

For each user story in the PRD, create a backlog task:

```bash
backlog task create "<title>" \
  -d "<description>" \
  --ac "<criterion1>,<criterion2>,Typecheck passes" \
  --priority <number>
```

For tasks with dependencies on earlier tasks:

```bash
backlog task create "<title>" \
  -d "<description>" \
  --ac "<criterion1>,<criterion2>,Typecheck passes" \
  --dep task-<id> \
  --priority <number>
```

---

## Story Size: The Number One Rule

**Each task must be completable in ONE Ralph iteration (one context window).**

Ralph spawns a fresh AI instance per iteration with no memory of previous work. If a task is too big, the LLM runs out of context before finishing and produces broken code.

### Right-sized tasks:
- Add a database column and migration
- Add a UI component to an existing page
- Update a server action with new logic
- Add a filter dropdown to a list

### Too big (split these):
- "Build the entire dashboard" - Split into: schema, queries, UI components, filters
- "Add authentication" - Split into: schema, middleware, login UI, session handling
- "Refactor the API" - Split into one task per endpoint or pattern

**Rule of thumb:** If you cannot describe the change in 2-3 sentences, it is too big.

---

## Story Ordering: Dependencies First

Create tasks in dependency order. Task IDs are auto-assigned sequentially, so create foundational tasks first (schema -> backend -> UI).

**Correct order:**
1. Schema/database changes (migrations)
2. Server actions / backend logic
3. UI components that use the backend
4. Dashboard/summary views that aggregate data

**Wrong order:**
1. UI component (depends on schema that does not exist yet)
2. Schema change

For tasks with explicit dependencies, use `--dep task-<id>`.

---

## Acceptance Criteria: Must Be Verifiable

Each criterion must be something Ralph can CHECK, not something vague.

### Good criteria (verifiable):
- "Add `status` column to tasks table with default 'pending'"
- "Filter dropdown has options: All, Active, Completed"
- "Clicking delete shows confirmation dialog"
- "Typecheck passes"
- "Tests pass"

### Bad criteria (vague):
- "Works correctly"
- "User can do X easily"
- "Good UX"
- "Handles edge cases"

### Always include as final criterion:
```
"Typecheck passes"
```

For tasks with testable logic, also include:
```
"Tests pass"
```

### For tasks that change UI, also include:
```
"Verify in browser using dev-browser skill"
```

Frontend tasks are NOT complete until visually verified. Ralph will use the dev-browser skill to navigate to the page, interact with the UI, and confirm changes work.

---

## Conversion Rules

1. **Each user story becomes one backlog task**
2. **Priority**: Based on dependency order, then document order
3. **Dependencies**: Use `--dep task-<id>` for tasks that depend on earlier ones
4. **Always add**: "Typecheck passes" to every task's acceptance criteria

---

## Splitting Large PRDs

If a PRD has big features, split them:

**Original:**
> "Add user notification system"

**Split into:**
1. Add notifications table to database
2. Create notification service for sending notifications
3. Add notification bell icon to header
4. Create notification dropdown panel
5. Add mark-as-read functionality
6. Add notification preferences page

Each is one focused change that can be completed and verified independently.

---

## Example

**Input PRD: "Task Priority System"**

```bash
backlog task create "Add priority field to database" \
  -d "As a developer, I need to store task priority so it persists across sessions." \
  --ac "Add priority column to tasks table,Generate and run migration,Typecheck passes" \
  --priority 1

backlog task create "Display priority indicator on task cards" \
  -d "As a user, I want to see task priority at a glance." \
  --ac "Each task card shows colored priority badge,Priority visible without hovering,Typecheck passes,Verify in browser using dev-browser skill" \
  --dep task-1 \
  --priority 2

backlog task create "Add priority selector to task edit" \
  -d "As a user, I want to change a task's priority when editing it." \
  --ac "Priority dropdown in task edit modal,Shows current priority as selected,Saves immediately on selection change,Typecheck passes,Verify in browser using dev-browser skill" \
  --dep task-2 \
  --priority 3

backlog task create "Filter tasks by priority" \
  -d "As a user, I want to filter the task list to see only high-priority items when I'm focused." \
  --ac "Filter dropdown with options: All | High | Medium | Low,Filter persists in URL params,Empty state message when no tasks match filter,Typecheck passes,Verify in browser using dev-browser skill" \
  --dep task-3 \
  --priority 4
```

---

## Checklist Before Creating Tasks

Before running the backlog task create commands, verify:

- [ ] Each task is completable in one iteration (small enough)
- [ ] Tasks are ordered by dependency (schema -> backend -> UI)
- [ ] Every task has "Typecheck passes" as criterion
- [ ] UI tasks have "Verify in browser using dev-browser skill" as criterion
- [ ] Acceptance criteria are verifiable (not vague)
- [ ] Dependencies are specified with `--dep task-<id>` where needed
