#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--tool amp|claude|opencode] [--model model_id] [--timeout minutes]
#                    [--on-error stop|continue|retry] [--retry-count N] [--log-file path]
#                    [--devcontainer] [max_iterations]

set -eo pipefail

# Parse arguments
TOOL="amp"  # Default to amp for backwards compatibility
MODEL="claude-opus-4-6"  # Default model for claude tool
TIMEOUT=15  # Per-iteration timeout in minutes
MAX_ITERATIONS=10
USE_DEVCONTAINER=false
ON_ERROR="stop"  # stop | continue | retry
RETRY_COUNT=2  # Number of retries for --on-error=retry
LOG_FILE=""  # Optional log file for errors

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
    --on-error)
      ON_ERROR="$2"
      shift 2
      ;;
    --on-error=*)
      ON_ERROR="${1#*=}"
      shift
      ;;
    --retry-count)
      RETRY_COUNT="$2"
      shift 2
      ;;
    --retry-count=*)
      RETRY_COUNT="${1#*=}"
      shift
      ;;
    --log-file)
      LOG_FILE="$2"
      shift 2
      ;;
    --log-file=*)
      LOG_FILE="${1#*=}"
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

# Validate tool choice
if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "opencode" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'amp', 'claude', or 'opencode'."
  exit 1
fi

# Validate timeout (minimum 1 minute)
if [[ ! "$TIMEOUT" =~ ^[0-9]+$ ]] || [[ "$TIMEOUT" -lt 1 ]]; then
  echo "Error: Timeout must be an integer >= 1 minute."
  exit 1
fi

# Validate on-error strategy
if [[ "$ON_ERROR" != "stop" && "$ON_ERROR" != "continue" && "$ON_ERROR" != "retry" ]]; then
  echo "Error: Invalid on-error strategy '$ON_ERROR'. Must be 'stop', 'continue', or 'retry'."
  exit 1
fi

# Validate retry-count
if [[ ! "$RETRY_COUNT" =~ ^[0-9]+$ ]] || [[ "$RETRY_COUNT" -lt 0 ]]; then
  echo "Error: Retry count must be a non-negative integer."
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

# Logging function
log_error() {
  local message="$1"
  local timestamp
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  if [[ -n "$LOG_FILE" ]]; then
    echo "[$timestamp] ERROR: $message" >> "$LOG_FILE"
  fi
  echo "[$timestamp] ERROR: $message" >&2
}

# Error handling function
handle_error() {
  local exit_code="$1"
  local iteration="$2"
  local retry_attempt="$3"
  
  log_error "Iteration $iteration failed with exit code $exit_code (tool: $TOOL, retry: $retry_attempt)"
  
  case "$ON_ERROR" in
    stop)
      echo "ERROR: AI tool failed with exit code $exit_code. Stopping."
      exit "$exit_code"
      ;;
    continue)
      echo "WARNING: AI tool failed with exit code $exit_code. Continuing to next iteration..."
      return 1  # Signal to continue loop
      ;;
    retry)
      if [[ $retry_attempt -lt $RETRY_COUNT ]]; then
        echo "WARNING: AI tool failed with exit code $exit_code. Retrying (attempt $((retry_attempt + 1)) of $RETRY_COUNT)..."
        return 2  # Signal to retry
      else
        echo "ERROR: AI tool failed after $RETRY_COUNT retries. Stopping."
        exit "$exit_code"
      fi
      ;;
  esac
}

MODEL_INFO=""
if [[ "$TOOL" == "claude" ]]; then
  MODEL_INFO=" ($MODEL)"
fi

CONFIG_INFO="on-error: $ON_ERROR"
[[ "$ON_ERROR" == "retry" ]] && CONFIG_INFO="$CONFIG_INFO (retries: $RETRY_COUNT)"
[[ -n "$LOG_FILE" ]] && CONFIG_INFO="$CONFIG_INFO, log: $LOG_FILE"

echo "Starting Ralph - Tool: $TOOL$MODEL_INFO - Max iterations: $MAX_ITERATIONS - Timeout: ${TIMEOUT}m${USE_DEVCONTAINER:+ (devcontainer)}"
echo "Config: $CONFIG_INFO"

for i in $(seq 1 "$MAX_ITERATIONS"); do
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
  trap 'rm -f "$OUTFILE"' EXIT

  # Build prompt with autonomous mode prefix
  MODE_PREFIX="MODE: autonomous (Ralph loop iteration $i of $MAX_ITERATIONS)"

  # Build the exec prefix for devcontainer mode
  EXEC_PREFIX=""
  if [[ "$USE_DEVCONTAINER" == true ]]; then
    EXEC_PREFIX="devcontainer exec --workspace-folder $SCRIPT_DIR"
  fi

  TIMEOUT_SEC=$((TIMEOUT * 60))

  # Retry loop for --on-error=retry
  retry_attempt=0
  while true; do
    if [[ "$TOOL" == "amp" ]]; then
      PROMPT=$(printf "%s\n\n%s" "$MODE_PREFIX" "$(cat "$SCRIPT_DIR/prompt.md")")
      echo "$PROMPT" | timeout "$TIMEOUT_SEC" ${EXEC_PREFIX:+$EXEC_PREFIX} amp --dangerously-allow-all 2>&1 | tee "$OUTFILE"
      EXIT_CODE=${PIPESTATUS[0]}
    elif [[ "$TOOL" == "opencode" ]]; then
      PROMPT="$MODE_PREFIX

Pick the next To Do task and execute the full Task Lifecycle from CLAUDE.md.
Your response MUST end with the ## Task Summary block. This is not optional."
      timeout "$TIMEOUT_SEC" ${EXEC_PREFIX:+$EXEC_PREFIX} opencode run "$PROMPT" 2>&1 | tee "$OUTFILE"
      EXIT_CODE=${PIPESTATUS[0]}
    else
      PROMPT="$MODE_PREFIX

Pick the next To Do task and execute the full Task Lifecycle from CLAUDE.md.
Your response MUST end with the ## Task Summary block. This is not optional."
      echo "$PROMPT" | timeout "$TIMEOUT_SEC" ${EXEC_PREFIX:+$EXEC_PREFIX} claude --model "$MODEL" --dangerously-skip-permissions --print 2>&1 | tee "$OUTFILE"
      EXIT_CODE=${PIPESTATUS[0]}
    fi

    # Check if iteration timed out (exit code 124 = timeout)
    if [[ $EXIT_CODE -eq 124 ]]; then
      echo ""
      echo "WARNING: Iteration $i timed out after ${TIMEOUT}m. Continuing to next iteration..."
      sleep 2
      break
    fi

    # Check for errors (non-zero exit code)
    if [[ $EXIT_CODE -ne 0 ]]; then
      handle_error "$EXIT_CODE" "$i" "$retry_attempt"
      handler_result=$?
      
      if [[ $handler_result -eq 1 ]]; then
        # continue strategy - go to next iteration
        break
      elif [[ $handler_result -eq 2 ]]; then
        # retry strategy - increment counter and retry
        retry_attempt=$((retry_attempt + 1))
        sleep 2
        continue
      fi
      # handler_result would be from exit(), but bash functions can't return that
      # The exit is handled inside handle_error for stop strategy
    fi

    # Success - break out of retry loop
    break
  done

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
