#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--tool amp|claude] [--model model_id] [--timeout minutes] [--devcontainer] [max_iterations]

set -eo pipefail

# Parse arguments
TOOL="amp"  # Default to amp for backwards compatibility
MODEL="claude-opus-4-6"  # Default model for claude tool
TIMEOUT=15  # Per-iteration timeout in minutes
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
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --timeout=*)
      TIMEOUT="${1#*=}"
      shift
      ;;
    --devcontainer)
      USE_DEVCONTAINER=true
      shift
      ;;
    *)
      # Assume it's max_iterations if it's a number
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

# Validate tool choice
if [[ "$TOOL" != "amp" && "$TOOL" != "claude" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'amp' or 'claude'."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verify backlog CLI is available
if ! command -v backlog &> /dev/null; then
  echo "Error: 'backlog' CLI not found. Install from https://github.com/MrLesk/Backlog.md"
  exit 1
fi

# Start devcontainer if requested
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
echo "Starting Ralph - Tool: $TOOL$MODEL_INFO - Max iterations: $MAX_ITERATIONS - Timeout: ${TIMEOUT}m${USE_DEVCONTAINER:+ (devcontainer)}"

for i in $(seq 1 $MAX_ITERATIONS); do
  # Check if any "To Do" tasks remain
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

  # Run the selected tool, saving output to temp file
  OUTFILE=$(mktemp)
  trap "rm -f $OUTFILE" EXIT

  # Build prompt with autonomous mode prefix
  MODE_PREFIX="MODE: autonomous (Ralph loop iteration $i of $MAX_ITERATIONS)"

  # Build the exec prefix for devcontainer mode
  EXEC_PREFIX=""
  if [[ "$USE_DEVCONTAINER" == true ]]; then
    EXEC_PREFIX="devcontainer exec --workspace-folder $SCRIPT_DIR"
  fi

  TIMEOUT_SEC=$((TIMEOUT * 60))

  if [[ "$TOOL" == "amp" ]]; then
    PROMPT=$(printf "%s\n\n%s" "$MODE_PREFIX" "$(cat "$SCRIPT_DIR/prompt.md")")
    echo "$PROMPT" | timeout "$TIMEOUT_SEC" $EXEC_PREFIX amp --dangerously-allow-all 2>&1 | tee "$OUTFILE"
    EXIT_CODE=$?
  else
    # Claude reads CLAUDE.md automatically as project instructions.
    # Send only a short, focused prompt — not the full CLAUDE.md — to avoid
    # drowning the key instructions in a wall of duplicated text.
    PROMPT="$MODE_PREFIX

Pick the next To Do task and execute the full Task Lifecycle from CLAUDE.md.
Your response MUST end with the ## Task Summary block. This is not optional."
    echo "$PROMPT" | timeout "$TIMEOUT_SEC" $EXEC_PREFIX claude --model "$MODEL" --dangerously-skip-permissions --print 2>&1 | tee "$OUTFILE"
    EXIT_CODE=$?
  fi

  # Check if iteration timed out (exit code 124 = timeout)
  if [[ $EXIT_CODE -eq 124 ]]; then
    echo ""
    echo "WARNING: Iteration $i timed out after ${TIMEOUT}m. Continuing to next iteration..."
    sleep 2
    continue
  fi

  # Check for completion signal
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
