Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Plan: Migrate Ralph from prd.json to Backlog.md CLI

 Overview

 Replace Ralph's single prd.json file with the
 backlog.md CLI tool for task management. Tasks become
 individual markdown files in backlog/tasks/ managed
 via backlog CLI commands.

 User Decisions

 - Branch name: Derive from task labels (e.g., label
 ralph/feature-name)
 - Progress tracking: Fully migrate to task notes
 (eliminate progress.txt)
 - Coexistence: Fully replace prd.json (no backward
 compatibility)
 - Task ordering: Default to task ID order; use
 priority if specified

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
 backlog.md: Label on tasks (e.g., ralph/feature-name)
 ────────────────────────────────────────
 prd.json: acceptanceCriteria[]
 backlog.md: ## Acceptance Criteria in task file
 ────────────────────────────────────────
 prd.json: progress.txt learnings
 backlog.md: --notes field in task file
 ---
 Files to Modify

 1. /Users/paul/Private/Projects/ralph/ralph.sh

 - Replace jq parsing of prd.json with backlog CLI
 calls
 - Change branch detection: extract from task labels
 - Update archive logic: archive backlog/ directory
 - Remove progress.txt initialization

 2. /Users/paul/Private/Projects/ralph/CLAUDE.md

 - Replace all prd.json references with backlog CLI
 commands
 - Update task selection: backlog task list -s "To Do"
 --plain
 - Update completion: backlog task edit <id> -s "Done"
 - Replace progress.txt append with backlog task edit
 <id> --notes "..."
 - Update stop condition logic

 3. /Users/paul/Private/Projects/ralph/prompt.md

 - Same changes as CLAUDE.md (for Amp CLI)

 4. /Users/paul/Private/Projects/ralph/skills/ralph/SKI
 LL.md

 - Change output from prd.json to backlog tasks
 - Use backlog task create commands
 - Update examples and checklists

 5.
 /Users/paul/Private/Projects/ralph/skills/prd/SKILL.md

 - Update to mention backlog.md as output target
 - Add note about ralph skill converting to backlog
 tasks

 6. /Users/paul/Private/Projects/ralph/README.md

 - Update workflow documentation
 - Change file descriptions
 - Update debugging commands

 7. /Users/paul/Private/Projects/ralph/AGENTS.md

 - Update key files section
 - Update patterns section

 ---
 Implementation Details

 Phase 1: ralph.sh Script

 Current flow:
 CURRENT_BRANCH=$(jq -r '.branchName' "$PRD_FILE")

 New flow:
 # Get branch from first task's ralph/* label
 CURRENT_BRANCH=$(backlog task list --plain 2>/dev/null
  | head -1 | grep -oE 'ralph/[^ ]+' || echo "")

 Task selection logic:
 # Check if any tasks remain (for completion detection
 in script)
 REMAINING=$(backlog task list -s "To Do" --plain
 2>/dev/null | wc -l)

 Archive logic:
 # Archive backlog/ directory instead of prd.json
 [ -d "$BACKLOG_DIR" ] && cp -r "$BACKLOG_DIR"
 "$ARCHIVE_FOLDER/"

 Phase 2: Agent Prompts (CLAUDE.md / prompt.md)

 Task Discovery:
 1. List pending tasks: `backlog task list -s "To Do"
 --plain`
 2. Pick the task with lowest ID (or highest priority
 if priorities exist)
 3. View task details: `backlog task <id> --plain`

 Task Selection Order:
 - Default: Pick lowest task ID where status is "To Do"
 - If tasks have `--priority` set: Pick highest
 priority first
 - Check for blockers: Skip tasks with unresolved
 `--dep` dependencies

 Branch Detection:
 - Read task labels to find branch name (e.g., label
 `ralph/feature-name`)
 - Extract: `backlog task list --plain | grep -oE
 'ralph/[^ ]+' | head -1`
 - If no ralph/* label found, use `main` or prompt user

 Marking Complete:
 - Update status: `backlog task edit <id> -s "Done"`
 - Add implementation notes: `backlog task edit <id>
 --notes "What was done, learnings..."`

 Stop Condition:
 - Check: `backlog task list -s "To Do" --plain`
 - If empty (no "To Do" tasks remain): output
 `<promise>COMPLETE</promise>`

 Progress/Learnings:
 - Instead of appending to progress.txt, add notes to
 task:
   `backlog task edit <id> --notes "## Implementation
 Notes\n- What was done\n- Learnings..."`
 - For cross-task patterns, update CLAUDE.md files as
 before

 Phase 3: Skills Updates

 skills/ralph/SKILL.md - New workflow:
 ## Output Format

 For each user story, run:
 backlog task create "<title>" \
   -d "<description>" \
   --ac "<criterion1>,<criterion2>,Typecheck passes" \
   -l ralph/<feature-name> \
   --priority <number>

 ## Example
 backlog task create "Add priority field to database" \
   -d "As a developer, I need to store task priority so
  it persists across sessions." \
   --ac "Add priority column to tasks table,Generate
 and run migration,Typecheck passes" \
   -l ralph/task-priority \
   --priority 1

 Dependency ordering:
 # For tasks that depend on earlier tasks:
 backlog task create "Display UI component" \
   -d "..." \
   --dep task-1 \
   --priority 2

 ---
 Verification Plan

 1. Create test backlog tasks:
 backlog init  # if needed
 backlog task create "Test task 1" -d "Test" --ac "Test
  criterion" -l ralph/test-feature
 backlog task create "Test task 2" -d "Test" --ac "Test
  criterion" -l ralph/test-feature
 2. Run ralph.sh and verify:
   - Script detects branch from labels
   - Script spawns AI instance
   - AI picks lowest ID task
   - AI implements (or simulates)
   - AI marks task Done via CLI
   - AI adds notes to task
   - Loop continues or completes
 3. Test completion detection:
   - Mark all tasks Done
   - Verify <promise>COMPLETE</promise> is output
   - Verify ralph.sh exits successfully
 4. Test archiving:
   - Change branch label on new tasks
   - Run ralph.sh
   - Verify old backlog/ is archived to
 archive/YYYY-MM-DD-feature/

 ---
 Files Summary
 File: ralph.sh
 Action: Modify
 Key Changes: Replace jq with backlog CLI, update
   archive logic
 ────────────────────────────────────────
 File: CLAUDE.md
 Action: Modify
 Key Changes: Full rewrite of task workflow
 instructions
 ────────────────────────────────────────
 File: prompt.md
 Action: Modify
 Key Changes: Same as CLAUDE.md for Amp
 ────────────────────────────────────────
 File: skills/ralph/SKILL.md
 Action: Modify
 Key Changes: Output backlog tasks instead of JSON
 ────────────────────────────────────────
 File: skills/prd/SKILL.md
 Action: Modify
 Key Changes: Minor updates to reference backlog
 ────────────────────────────────────────
 File: README.md
 Action: Modify
 Key Changes: Update workflow docs, file descriptions
 ────────────────────────────────────────
 File: AGENTS.md
 Action: Modify
 Key Changes: Update key files and patterns
 ────────────────────────────────────────
 File: prd.json.example
 Action: Delete
 Key Changes: No longer needed
 ────────────────────────────────────────
 File: progress.txt
 Action: Delete concept
 Key Changes: Learnings go to task notes
 ---
 Commit Strategy

 1. feat: Replace prd.json with backlog.md CLI in
 ralph.sh
 2. feat: Update CLAUDE.md for backlog workflow
 3. feat: Update prompt.md for backlog workflow
 4. feat: Update ralph skill for backlog task creation
 5. docs: Update README and AGENTS.md for backlog
 workflow
 6. chore: Remove prd.json.example
