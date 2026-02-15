---
name: ralph-init
description: "Bootstrap Ralph autonomous agent infrastructure in a new project. Sets up ralph.sh, CLAUDE.md, git hooks, backlog, .devcontainer, .gitignore, and skills. Triggers on: ralph init, bootstrap ralph, setup ralph, init ralph, initialize ralph."
---

# Ralph Project Bootstrapper

Set up Ralph autonomous agent infrastructure in an existing git repository.

---

## The Job

1. Confirm the current directory is a git repository
2. Ask clarifying questions about the project
3. Copy/generate all Ralph infrastructure files
4. Initialize backlog
5. Report what was created

**Important:** Do NOT start implementing features or creating tasks. Just set up the infrastructure.

---

## Step 1: Preflight Checks

Before anything else, verify:

```bash
# Must be a git repo
git rev-parse --git-dir

# Check if backlog CLI is installed
command -v backlog
```

If `backlog` is not installed, tell the user:
```
Install backlog.md CLI first: npm install -g backlog.md
```

If not a git repo, tell the user to run `git init` first.

---

## Step 2: Clarifying Questions

Ask these questions with lettered options:

```
1. What is your primary language/runtime?
   A. TypeScript / Node.js
   B. Python
   C. Go
   D. Other: [please specify]

2. What are your quality check commands?
   A. npm run build && npm run lint && npm test
   B. pytest && mypy . && ruff check .
   C. go build ./... && go vet ./... && go test ./...
   D. Other: [please specify]

3. Do you need the DevContainer (sandboxed execution with firewall)?
   A. Yes — I want isolated autonomous runs
   B. No — I'll run Ralph directly on my machine

4. Which AI tool will you use with Ralph?
   A. Claude Code only
   B. Amp only
   C. Both Claude Code and Amp
```

---

## Step 3: Generate Files

Generate the following files. **Skip any file that already exists** unless the user says `--force`.

### 3.1 `ralph.sh` (project root)

Copy the ralph.sh script. This is the main loop that spawns AI instances.

```bash
#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--tool amp|claude] [--model model_id] [--devcontainer] [max_iterations]

set -e

# Parse arguments
TOOL="amp"
MODEL="claude-opus-4-6"
MAX_ITERATIONS=10
USE_DEVCONTAINER=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --model=*)
      MODEL="${1#*=}"
      shift
      ;;
    --devcontainer)
      USE_DEVCONTAINER=true
      shift
      ;;
    *)
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

if [[ "$TOOL" != "amp" && "$TOOL" != "claude" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'amp' or 'claude'."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v backlog &> /dev/null; then
  echo "Error: 'backlog' CLI not found. Install from https://github.com/MrLesk/Backlog.md"
  exit 1
fi

if [[ "$USE_DEVCONTAINER" == true ]]; then
  if ! command -v devcontainer &> /dev/null; then
    echo "Error: 'devcontainer' CLI not found. Install with: npm install -g @devcontainers/cli"
    exit 1
  fi
  echo "Starting devcontainer..."
  devcontainer up --workspace-folder "$SCRIPT_DIR"
  echo "Devcontainer is ready."
fi

MODEL_INFO=""
if [[ "$TOOL" == "claude" ]]; then
  MODEL_INFO=" ($MODEL)"
fi
echo "Starting Ralph - Tool: $TOOL$MODEL_INFO - Max iterations: $MAX_ITERATIONS${USE_DEVCONTAINER:+ (devcontainer)}"

for i in $(seq 1 $MAX_ITERATIONS); do
  TODO_OUTPUT=$(backlog task list -s "To Do" --plain 2>/dev/null)
  if echo "$TODO_OUTPUT" | grep -q "No tasks found"; then
    echo ""
    echo "All tasks complete!"
    exit 0
  fi

  echo ""
  echo "==============================================================="
  REMAINING=$(echo "$TODO_OUTPUT" | grep -c "TASK-" || echo "0")
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL) - $REMAINING tasks remaining"
  echo "==============================================================="

  OUTFILE=$(mktemp)
  trap "rm -f $OUTFILE" EXIT

  MODE_PREFIX="MODE: autonomous (Ralph loop iteration $i of $MAX_ITERATIONS)"

  EXEC_PREFIX=""
  if [[ "$USE_DEVCONTAINER" == true ]]; then
    EXEC_PREFIX="devcontainer exec --workspace-folder $SCRIPT_DIR"
  fi

  if [[ "$TOOL" == "amp" ]]; then
    PROMPT=$(printf "%s\n\n%s" "$MODE_PREFIX" "$(cat "$SCRIPT_DIR/prompt.md")")
    echo "$PROMPT" | $EXEC_PREFIX amp --dangerously-allow-all 2>&1 | tee "$OUTFILE" || true
  else
    PROMPT="$MODE_PREFIX

Pick the next To Do task and execute the full Task Lifecycle from CLAUDE.md.
Your response MUST end with the ## Task Summary block. This is not optional."
    echo "$PROMPT" | $EXEC_PREFIX claude --model "$MODEL" --dangerously-skip-permissions --print 2>&1 | tee "$OUTFILE" || true
  fi

  if grep -q "<promise>COMPLETE</promise>" "$OUTFILE"; then
    echo ""
    echo "Ralph completed all tasks!"
    echo "Completed at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi

  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check remaining tasks with: backlog task list --plain"
exit 1
```

Make it executable: `chmod +x ralph.sh`

### 3.2 `CLAUDE.md` (project root)

Write the CLAUDE.md file using the template below. The `## Project-Specific` section at the bottom MUST be filled in based on the user's answers from Step 2 (language, build/lint/test commands, framework, conventions).

**Template:**

````markdown
# Agent Instructions

## CRITICAL: One Task Per Iteration (Autonomous Mode)

If the prompt starts with `MODE: autonomous`: you MUST complete exactly **ONE** task, then **STOP**. Do NOT pick up another task. The Ralph loop will spawn a fresh instance for the next task.

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

## Ralph Loop (Autonomous Mode)

Activated when the prompt starts with `MODE: autonomous`. Task picking:

1. Run: `backlog task list -s "To Do" --plain` (pick lowest ID, or highest priority)
2. Read details: `backlog task <id> --plain`
3. Execute the Task Lifecycle above for that single task
4. Then STOP (see top of file)

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
````

**Important:** Replace ALL `<FILL IN ...>` placeholders with actual values from the user's answers. Parse the quality check commands (Q2) into separate build, lint, and test entries. If the user gave a single combined command, split it logically.

### 3.3 `.git/hooks/post-commit`

Install the post-commit hook that appends commit hashes to task files:

```bash
#!/bin/bash

# Skip if only backlog files changed (avoid noise on task-only commits)
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)
if echo "$CHANGED_FILES" | grep -qE '^backlog/'; then
    if ! echo "$CHANGED_FILES" | grep -qvE '^backlog/'; then
        exit 0
    fi
fi

BRANCH_NAME=$(git symbolic-ref --short HEAD 2>/dev/null)
TASK_ID=$(echo "$BRANCH_NAME" | grep -oE 'task-[0-9]+' | head -1)

if [ -n "$TASK_ID" ]; then
    NUMERIC_ID="${TASK_ID#task-}"

    IS_AMEND=false
    if git reflog -1 --format=%gs | grep -q "amend"; then
        IS_AMEND=true
    fi

    COMMIT_HASH=$(git rev-parse --short HEAD)
    COMMIT_MSG=$(git log -1 --format=%s)
    TASK_FILE=$(ls "$(git rev-parse --show-toplevel)"/backlog/tasks/task-"${NUMERIC_ID}"*.md 2>/dev/null | head -1)

    if [ "$IS_AMEND" = true ] && [ -n "$TASK_FILE" ]; then
        PREV_HASH=$(git reflog -2 --format=%h | tail -1)
        if grep -q "Commit: \`$PREV_HASH\`" "$TASK_FILE" 2>/dev/null; then
            sed -i '' "s/Commit: \`$PREV_HASH\` - .*/Commit: \`$COMMIT_HASH\` - $COMMIT_MSG/" "$TASK_FILE"
        else
            backlog task edit "$NUMERIC_ID" --append-notes "Commit: \`$COMMIT_HASH\` - $COMMIT_MSG" 2>/dev/null || true
        fi
    else
        backlog task edit "$NUMERIC_ID" --append-notes "Commit: \`$COMMIT_HASH\` - $COMMIT_MSG" 2>/dev/null || true
    fi
fi
```

Make it executable: `chmod +x .git/hooks/post-commit`

**Important:** If `.git/hooks/post-commit` already exists, warn the user and ask before overwriting.

### 3.4 `.gitignore` additions

Append these entries to `.gitignore` (create if missing). Only add lines that are not already present:

```
# Ralph / Claude
.claude/
.DS_Store
```

Do NOT add `backlog/` — task files should be committed.

### 3.5 Backlog initialization

```bash
backlog init
```

Skip if `backlog/` directory already exists.

### 3.6 `.devcontainer/` (only if user said Yes)

Generate three files:

- `.devcontainer/Dockerfile` — use the template from the Ralph repo, replacing Stage 1 with the correct language runtime based on the user's answer
- `.devcontainer/devcontainer.json` — use the template, update the app label and port if the user specifies
- `.devcontainer/init-firewall.sh` — copy as-is from the Ralph repo

### 3.7 `.claude/settings.local.json`

Generate with permission allowlist for backlog and git operations. Use the project's absolute path:

```json
{
  "permissions": {
    "allow": [
      "Bash(backlog --help:*)",
      "Bash(backlog status)",
      "Bash(backlog task --help:*)",
      "Bash(backlog task create:*)",
      "Bash(backlog task edit:*)",
      "Bash(backlog task list:*)",
      "Bash(backlog init:*)",
      "Bash(backlog doc:*)",
      "Bash(backlog overview)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git config:*)"
    ]
  }
}
```

---

## Step 4: Summary

After generating all files, print a summary:

```
Ralph initialized successfully!

Files created:
  ralph.sh              - Main autonomous loop script
  CLAUDE.md             - Agent instructions for Claude Code
  .git/hooks/post-commit - Commit hash tracking for tasks
  .gitignore            - Updated with Ralph entries
  backlog/              - Backlog initialized
  .claude/settings.local.json - Claude Code permissions
  .devcontainer/        - (if applicable) Sandboxed execution environment

Next steps:
  1. Review and customize CLAUDE.md (especially ## Project-Specific)
  2. Create a PRD:  /ralph-prd
  3. Convert to tasks:  /ralph-backlog
  4. Run Ralph:  ./ralph.sh --tool claude
```

---

## Idempotency

- **Never overwrite existing files** without asking
- If a file exists, print `[skip] CLAUDE.md already exists (use --force to overwrite)`
- For `.gitignore`, only append missing entries
- For `.git/hooks/post-commit`, warn if a hook already exists and ask before replacing
- `backlog init` is safe to skip if `backlog/` already exists

---

## Checklist

Before finishing:

- [ ] Confirmed git repo exists
- [ ] Asked clarifying questions
- [ ] Generated ralph.sh (executable)
- [ ] Generated CLAUDE.md with project-specific section filled in
- [ ] Installed post-commit git hook (executable)
- [ ] Updated .gitignore
- [ ] Ran backlog init (or skipped if exists)
- [ ] Generated .devcontainer if requested
- [ ] Generated .claude/settings.local.json
- [ ] Printed summary with next steps
