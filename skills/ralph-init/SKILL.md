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

Generate CLAUDE.md with the full agent instructions. Fill in the `## Project-Specific` section at the bottom based on the user's answers:

- Language/framework
- Build, lint, and test commands
- Any conventions mentioned

Use the CLAUDE.md from the Ralph repo as the template. The `## Project-Specific` section should look like:

```markdown
## Project-Specific

- **Language:** TypeScript (or whatever they said)
- **Build:** `npm run build`
- **Lint:** `npm run lint`
- **Test:** `npm test`
- **Framework:** (if mentioned)

### Conventions
- (Add any conventions the user mentioned, or leave a placeholder)
```

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
