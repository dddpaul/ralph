#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--tool amp|claude|opencode] [--model model_id] [--effort low|medium|high|max]
#                    [--timeout minutes] [--on-error stop|continue|retry] [--retry-count N]
#                    [--log-file path] [--devcontainer] [max_iterations]

set -o pipefail

# Parse arguments
TOOL="amp"  # Default to amp for backwards compatibility
MODEL="claude-opus-4-6"  # Default model for claude tool
EFFORT="medium"  # Default effort level for claude tool (low|medium|high|max)
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
    --effort)
      EFFORT="$2"
      shift 2
      ;;
    --effort=*)
      EFFORT="${1#*=}"
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

# Validate effort level
if [[ "$EFFORT" != "low" && "$EFFORT" != "medium" && "$EFFORT" != "high" && "$EFFORT" != "max" ]]; then
  echo "Error: Invalid effort level '$EFFORT'. Must be 'low', 'medium', 'high', or 'max'."
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

# Source summary library
source "$SCRIPT_DIR/lib/summary.sh"

# Run tracking state
RUN_START_TIME=$(date +%s)
TASKS_COMPLETED=0
FAILED_ITERATIONS=0
ITER_DURATIONS=()
EXIT_REASON=""

count_remaining_tasks() {
  local output
  output=$(backlog task list -s "To Do" --plain 2>/dev/null)
  if echo "$output" | grep -q "No tasks found"; then
    echo "0"
  else
    echo "$output" | grep -c "TASK-" || echo "0"
  fi
}

show_summary() {
  local reason="${1:-$EXIT_REASON}"
  local wall_time=$(( $(date +%s) - RUN_START_TIME ))
  local remaining
  remaining=$(count_remaining_tasks)
  print_summary "$TASKS_COMPLETED" "$wall_time" "${#ITER_DURATIONS[@]}" "$MAX_ITERATIONS" "$reason" "$remaining" "$FAILED_ITERATIONS" "${ITER_DURATIONS[@]}"
}

cleanup_and_exit() {
  local code="$1"
  show_summary
  exit "$code"
}

_ralph_cleanup_files=()
_ralph_cleanup() { rm -f "${_ralph_cleanup_files[@]}"; }
trap '_ralph_cleanup' EXIT
trap 'EXIT_REASON="interrupted"; show_summary "interrupted"; exit 130' INT TERM

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

# Format seconds as human-readable duration
format_duration() {
  local seconds="$1"
  local hours=$((seconds / 3600))
  local minutes=$(( (seconds % 3600) / 60 ))
  local secs=$((seconds % 60))

  if [[ $hours -gt 0 ]]; then
    printf "%dh %dm %ds" "$hours" "$minutes" "$secs"
  elif [[ $minutes -gt 0 ]]; then
    printf "%dm %ds" "$minutes" "$secs"
  else
    printf "%ds" "$secs"
  fi
}

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
      EXIT_REASON="error"
      FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
      ITER_DURATIONS+=("$(( $(date +%s) - ITER_START ))")
      cleanup_and_exit "$exit_code"
      ;;
    continue)
      echo "WARNING: AI tool failed with exit code $exit_code. Continuing to next iteration..."
      FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
      return 1  # Signal to continue loop
      ;;
    retry)
      if [[ $retry_attempt -lt $RETRY_COUNT ]]; then
        echo "WARNING: AI tool failed with exit code $exit_code. Retrying (attempt $((retry_attempt + 1)) of $RETRY_COUNT)..."
        return 2  # Signal to retry
      else
        echo "ERROR: AI tool failed after $RETRY_COUNT retries. Stopping."
        EXIT_REASON="error"
        FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
        ITER_DURATIONS+=("$(( $(date +%s) - ITER_START ))")
        cleanup_and_exit "$exit_code"
      fi
      ;;
  esac
}

MODEL_INFO=""
if [[ "$TOOL" == "claude" ]]; then
  MODEL_INFO=" ($MODEL, effort: $EFFORT)"
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
    EXIT_REASON="all tasks done"
    cleanup_and_exit 0
  fi

  ITER_START=$(date +%s)

  echo ""
  echo "==============================================================="
  REMAINING=$(echo "$TODO_OUTPUT" | grep -c "TASK-" || echo "0")
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL) - $REMAINING tasks remaining"
  echo "==============================================================="

  # Run the selected tool, saving output to temp file
  OUTFILE=$(mktemp)
  _ralph_cleanup_files+=("$OUTFILE")

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
      timeout "$TIMEOUT_SEC" ${EXEC_PREFIX:+$EXEC_PREFIX} amp --dangerously-allow-all <<< "$PROMPT" 2>&1 | tee "$OUTFILE"
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
      timeout "$TIMEOUT_SEC" ${EXEC_PREFIX:+$EXEC_PREFIX} claude --model "$MODEL" --effort "$EFFORT" --dangerously-skip-permissions --print <<< "$PROMPT" 2>&1 | tee "$OUTFILE"
      EXIT_CODE=${PIPESTATUS[0]}
    fi

    # Check if iteration timed out (exit code 124 = timeout)
    ITER_FAILED=false
    if [[ $EXIT_CODE -eq 124 ]]; then
      echo ""
      echo "WARNING: Iteration $i timed out after ${TIMEOUT}m ($(format_duration $(($(date +%s) - ITER_START)))). Continuing to next iteration..."
      FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
      ITER_FAILED=true
      sleep 2
      break
    fi

    # Check for errors (non-zero exit code)
    if [[ $EXIT_CODE -ne 0 ]]; then
      handle_error "$EXIT_CODE" "$i" "$retry_attempt"
      handler_result=$?

      if [[ $handler_result -eq 1 ]]; then
        # continue strategy - go to next iteration
        ITER_FAILED=true
        break
      elif [[ $handler_result -eq 2 ]]; then
        # retry strategy - increment counter and retry
        retry_attempt=$((retry_attempt + 1))
        sleep 2
        continue
      fi
    fi

    # Success - break out of retry loop
    break
  done

  ITER_ELAPSED=$(( $(date +%s) - ITER_START ))
  ITER_DURATIONS+=("$ITER_ELAPSED")

  if [[ "$ITER_FAILED" == true ]]; then
    echo "Iteration $i failed ($(format_duration $ITER_ELAPSED)). Continuing..."
    sleep 2
    continue
  fi

  TASKS_COMPLETED=$((TASKS_COMPLETED + 1))

  # Check for completion signal
  if grep -q "<promise>COMPLETE</promise>" "$OUTFILE"; then
    EXIT_REASON="all tasks done"
    cleanup_and_exit 0
  fi

  echo "Iteration $i complete ($(format_duration $ITER_ELAPSED)). Continuing..."
  sleep 2
done

EXIT_REASON="max iterations reached"
cleanup_and_exit 1
