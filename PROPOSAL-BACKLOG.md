Plan: Migrate Ralph from prd.json to Backlog.md CLI

 Overview

 Replace Ralph's single prd.json file with the
 backlog.md CLI tool. Each task becomes its own branch
 (task-<id>), gets merged to main after completion, and
  Ralph loops through all tasks.

 User Decisions

 - Branch name: task-<id> per task (e.g., task-5)
 - Progress tracking: Fully migrate to task notes
 (eliminate progress.txt)
 - Coexistence: Fully replace prd.json (no backward
 compatibility)
 - Task ordering: Default to task ID order; use
 priority if specified
 - Merge strategy: Merge each task branch directly to
 main
 - Loop behavior: Ralph loops through all tasks in one
 run

 New Workflow

 1. backlog task list -s "To Do" --plain → pick next
 task (lowest ID or highest priority)
 2. git checkout -b task-<id> main
 3. backlog task edit <id> -s "In Progress"
 4. View task details: backlog task <id> --plain
 5. Implement the task
 6. Run quality checks
 7. Commit: feat: task-<id> - <title>
 8. git checkout main && git merge task-<id>
 9. backlog task edit <id> -s "Done" --notes
 "Implementation notes..."
 10. Check remaining tasks → loop or output
 <promise>COMPLETE</promise>

 ---
 Key Mappings
 prd.json: passes: false
 backlog.md: Status: "To Do"
 ────────────────────────────────────────
 prd.json: passes: true
 backlog.md: Status: "Done"
 ────────────────────────────────────────
 prd.json: priority: 1,2,3
 backlog.md: Task ID order (or --priority flag)
 ────────────────────────────────────────
 prd.json: branchName
 backlog.md: Derived: task-<id>
 ────────────────────────────────────────
 prd.json: acceptanceCriteria[]
 backlog.md: --ac flag / ## Acceptance Criteria
 ────────────────────────────────────────
 prd.json: progress.txt learnings
 backlog.md: --notes on the task
 ---
 Files to Modify

 1. ralph.sh — Core loop rewrite

 Remove:
 - PRD_FILE / jq parsing
 - PROGRESS_FILE initialization
 - .last-branch tracking
 - Archive logic (no longer needed — each task is its
 own branch)

 Add:
 - Task discovery via backlog task list -s "To Do"
 --plain
 - Per-task branching: git checkout -b task-<id> main
 - Per-task merging: git checkout main && git merge
 task-<id>
 - Completion check: no "To Do" tasks remaining

 New script structure:
 #!/bin/bash
 set -e

 TOOL="amp"
 MAX_ITERATIONS=10
 # parse args...

 echo "Starting Ralph - Tool: $TOOL - Max iterations:
 $MAX_ITERATIONS"

 for i in $(seq 1 $MAX_ITERATIONS); do
   # Check if any "To Do" tasks remain
   REMAINING=$(backlog task list -s "To Do" --plain
 2>/dev/null | grep -c "^" || echo "0")
   if [ "$REMAINING" -eq 0 ]; then
     echo "All tasks complete!"
     exit 0
   fi

   echo "=== Ralph Iteration $i of $MAX_ITERATIONS
 ($TOOL) ==="

   # Spawn AI instance with prompt
   if [[ "$TOOL" == "amp" ]]; then
     OUTPUT=$(cat prompt.md | amp
 --dangerously-allow-all 2>&1 | tee /dev/stderr) ||
 true
   else
     OUTPUT=$(claude --dangerously-skip-permissions
 --print < CLAUDE.md 2>&1 | tee /dev/stderr) || true
   fi

   # Check for completion signal
   if echo "$OUTPUT" | grep -q
 "<promise>COMPLETE</promise>"; then
     echo "Ralph completed all tasks!"
     exit 0
   fi

   sleep 2
 done

 echo "Reached max iterations ($MAX_ITERATIONS)."
 exit 1

 2. CLAUDE.md — Full rewrite for backlog workflow

 New content structure:

 # Ralph Agent Instructions

 ## Your Task

 1. List pending tasks: `backlog task list -s "To Do"
 --plain`
 2. Pick the next task:
    - Default: lowest task ID
    - If priorities exist: highest priority first
 3. Read task details: `backlog task <id> --plain`
 4. Create branch: `git checkout -b task-<id> main`
 5. Mark in progress: `backlog task edit <id> -s "In
 Progress"`
 6. Implement the task
 7. Run quality checks (typecheck, lint, test)
 8. Update CLAUDE.md files if you discover reusable
 patterns
 9. If checks pass, commit: `feat: task-<id> - <title>`
 10. Merge to main: `git checkout main && git merge
 task-<id>`
 11. Mark done: `backlog task edit <id> -s "Done"`
 12. Add implementation notes: `backlog task edit <id>
 --notes "..."`

 ## Implementation Notes Format

 Add notes to the completed task (via --notes flag):
 - What was implemented
 - Files changed
 - Learnings for future iterations

 ## Codebase Patterns

 If you discover reusable patterns, update nearby
 CLAUDE.md files.
 (Same section as current — no changes needed)

 ## Quality Requirements
 (Same as current — no changes)

 ## Browser Testing
 (Same as current — no changes)

 ## Stop Condition

 After completing a task:
 1. Run: `backlog task list -s "To Do" --plain`
 2. If NO tasks remain with status "To Do": reply with
 <promise>COMPLETE</promise>
 3. If tasks remain: end normally (next iteration picks
  up)

 ## Important

 - Work on ONE task per iteration
 - Each task gets its own branch: `task-<id>`
 - Always merge to main before finishing
 - Use `--plain` flag for all backlog CLI output

 3. prompt.md — Same changes as CLAUDE.md (for Amp)

 Mirror all CLAUDE.md changes, keeping Amp-specific
 differences (thread URL format).

 4. skills/ralph/SKILL.md — Output backlog tasks
 instead of JSON

 Replace the JSON output format section with:

 ## Output Format

 For each user story in the PRD, create a backlog task:

 backlog task create "<title>" \
   -d "<description>" \
   --ac "<criterion1>,<criterion2>,Typecheck passes" \
   --priority <number>

 ## Story Ordering
 Create tasks in dependency order. Task IDs are
 auto-assigned sequentially,
 so create foundational tasks first (schema → backend →
  UI).

 For tasks with dependencies:
 backlog task create "<title>" --dep task-<id>

 ## Example

 Input PRD: "Task Priority System"

 backlog task create "Add priority field to database" \
   -d "As a developer, I need to store task priority so
  it persists across sessions." \
   --ac "Add priority column to tasks table,Generate
 and run migration,Typecheck passes" \
   --priority 1

 backlog task create "Display priority indicator on
 task cards" \
   -d "As a user, I want to see task priority at a
 glance." \
   --ac "Each task card shows colored priority
 badge,Priority visible without hovering,Typecheck
 passes,Verify in browser" \
   --dep task-1 \
   --priority 2

 5. skills/prd/SKILL.md — Minor update

 Add a note at the end:
 ## Next Step
 After creating the PRD, use the Ralph skill to convert
  it to backlog tasks:
 "Load the ralph skill and convert
 tasks/prd-[feature-name].md to backlog tasks"

 6. README.md — Update documentation

 Key changes:
 - Replace prd.json references with backlog.md CLI
 - Update workflow section (backlog init → task create
 → ralph.sh)
 - Update key files table (remove prd.json, add
 backlog/)
 - Update debugging section (backlog task list --plain
 instead of jq)
 - Remove archiving section (no longer applicable with
 per-task branches)

 7. AGENTS.md — Update key files and patterns

 - Replace prd.json references with backlog/tasks/
 - Update "Memory persists via" to include backlog task
  notes
 - Remove progress.txt references

 8. Update PROMPT-BACKLOG.md — Write the full proposal

 Replace current content with the complete migration
 proposal documenting:
 - The new workflow (backlog CLI replaces prd.json)
 - Per-task branching strategy (task-<id>)
 - Merge-to-main after each task
 - Task ordering (ID order, priority override)
 - Progress via task notes (no progress.txt)
 - All affected files and their changes

 9. Delete prd.json.example

 No longer needed — backlog.md format replaces it.

 ---
 Verification Plan

 1. Ensure backlog CLI is available:
 which backlog && backlog --version
 2. Create test tasks:
 backlog init  # if needed
 backlog task create "Test task 1" -d "First test" --ac
  "Criterion A,Criterion B"
 backlog task create "Test task 2" -d "Second test"
 --ac "Criterion C" --dep task-1
 3. Verify ralph.sh flow:
   - Run ./ralph.sh --tool claude 1 (single iteration)
   - Verify branch task-1 is created
   - Verify task is marked "In Progress" then "Done"
   - Verify merge to main
 4. Test completion:
   - Mark all tasks Done manually
   - Verify ralph.sh detects no remaining tasks and
 exits 0
 5. Test task ordering:
   - Create tasks with explicit --priority values
   - Verify Ralph picks highest priority first
