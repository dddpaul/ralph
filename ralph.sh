#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--tool claude|opencode] [--model model_id] [--effort low|medium|high|max]
#                    [--timeout minutes] [--on-error stop|continue|retry] [--retry-count N]
#                    [--log-file path] [--devcontainer] [max_iterations]

set -o pipefail

# Parse arguments
TOOL="claude"
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
if [[ "$TOOL" != "claude" && "$TOOL" != "opencode" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'claude' or 'opencode'."
  exit 1
fi

# Validate timeout (any positive number of minutes)
if ! echo "$TIMEOUT" | grep -qE '^[0-9]*\.?[0-9]+$' || awk "BEGIN{exit(!($TIMEOUT <= 0))}"; then
  echo "Error: Timeout must be a positive number of minutes."
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Source libraries
source "$SCRIPT_DIR/lib/summary.sh"
source "$SCRIPT_DIR/lib/status.sh"

# Run tracking state
RUN_START_TIME=$(date +%s)
TASKS_COMPLETED=0
FAILED_ITERATIONS=0
ITER_DURATIONS=()
EXIT_REASON=""

# Status file tracking
STATUS_FILE="${RALPH_STATUS_FILE:-$SCRIPT_DIR/backlog/.ralph-status.json}"
RUN_LOG="${RALPH_RUN_LOG:-$SCRIPT_DIR/backlog/.ralph-run.log}"
RUN_STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TASKS_DONE_IDS=""
STATUS_ERRORS=""
CURRENT_TASK=""
LAST_ITER_DURATION=""
CURRENT_ITERATION=0

count_remaining_tasks() {
  local output
  output=$(backlog task list -s "To Do" --plain 2>/dev/null)
  if echo "$output" | grep -q "No tasks found"; then
    echo "0"
  else
    echo "$output" | grep -c "TASK-" || echo "0"
  fi
}

_get_done_task_ids() {
  backlog task list -s "Done" --plain 2>/dev/null | grep -o "TASK-[0-9]*" | sort || true
}

_update_status() {
  local state="$1"
  local completed_at="${2:-}"
  local exit_code="${3:-}"
  local elapsed=$(( $(date +%s) - RUN_START_TIME ))
  local remaining
  remaining=$(count_remaining_tasks)
  write_status "$STATUS_FILE" "$$" "$RUN_STARTED_AT" "$state" \
    "$CURRENT_ITERATION" "$MAX_ITERATIONS" "$TOOL" "$remaining" \
    "$CURRENT_TASK" "$LAST_ITER_DURATION" "$elapsed" "$completed_at" \
    "$exit_code" "$TASKS_DONE_IDS" "$STATUS_ERRORS"
}

_append_status_error() {
  if [[ -n "$STATUS_ERRORS" ]]; then
    STATUS_ERRORS="$STATUS_ERRORS"$'\n'"$1"
  else
    STATUS_ERRORS="$1"
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
  local final_state="completed"
  [[ "$code" -ne 0 ]] && final_state="failed"
  _update_status "$final_state" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$code"
  show_summary
  exit "$code"
}

_ralph_cleanup_files=()
_ralph_cleanup() { rm -f "${_ralph_cleanup_files[@]}"; }
trap '_ralph_cleanup' EXIT
_ralph_interrupt() {
  EXIT_REASON="interrupted"
  _update_status "failed" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "130"
  show_summary "interrupted"
  exit 130
}
trap '_ralph_interrupt' INT TERM

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
  _append_status_error "Iteration $iteration failed with exit code $exit_code"

  case "$ON_ERROR" in
    stop)
      echo "ERROR: AI tool failed with exit code $exit_code. Stopping."
      EXIT_REASON="error"
      LAST_ITER_DURATION=$(( $(date +%s) - ITER_START ))
      FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
      ITER_DURATIONS+=("$LAST_ITER_DURATION")
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
        LAST_ITER_DURATION=$(( $(date +%s) - ITER_START ))
        FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
        ITER_DURATIONS+=("$LAST_ITER_DURATION")
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

# Set up run logging
mkdir -p "$SCRIPT_DIR/backlog"
: > "$RUN_LOG"
exec > >(tee -a "$RUN_LOG") 2>&1

_update_status "running"

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
  CURRENT_ITERATION=$i
  DONE_BEFORE=$(_get_done_task_ids)
  CURRENT_TASK=$(echo "$TODO_OUTPUT" | grep -o "TASK-[0-9]*" | head -1)
  _update_status "running"

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

  TIMEOUT_SEC=$(awk "BEGIN{printf \"%d\", $TIMEOUT * 60}")

  # Retry loop for --on-error=retry
  retry_attempt=0
  while true; do
    if [[ "$TOOL" == "opencode" ]]; then
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
      _append_status_error "Iteration $i timed out after ${TIMEOUT}m"
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

  # Verify agent produced exactly one Task Summary block
  if ! grep -q '<promise>COMPLETE</promise>' "$OUTFILE"; then
    SUMMARY_COUNT=$(grep -c '^## Task Summary$' "$OUTFILE" || true)
    if [[ "$SUMMARY_COUNT" -ne 1 ]]; then
      echo "WARNING: Iteration $i produced $SUMMARY_COUNT '## Task Summary' blocks (expected 1). This may indicate the agent processed multiple tasks or none." >&2
    fi
  fi

  ITER_ELAPSED=$(( $(date +%s) - ITER_START ))
  ITER_DURATIONS+=("$ITER_ELAPSED")
  LAST_ITER_DURATION="$ITER_ELAPSED"

  # Track tasks that transitioned to Done during this iteration
  DONE_AFTER=$(_get_done_task_ids)
  if [[ -n "$DONE_AFTER" ]]; then
    NEW_DONE=""
    if [[ -n "$DONE_BEFORE" ]]; then
      NEW_DONE=$(comm -13 <(echo "$DONE_BEFORE") <(echo "$DONE_AFTER"))
    else
      NEW_DONE="$DONE_AFTER"
    fi
    if [[ -n "$NEW_DONE" ]]; then
      if [[ -n "$TASKS_DONE_IDS" ]]; then
        TASKS_DONE_IDS="$TASKS_DONE_IDS"$'\n'"$NEW_DONE"
      else
        TASKS_DONE_IDS="$NEW_DONE"
      fi
    fi
  fi

  if [[ "$ITER_FAILED" == true ]]; then
    _update_status "running"
    echo "Iteration $i failed ($(format_duration $ITER_ELAPSED)). Continuing..."
    sleep 2
    continue
  fi

  TASKS_COMPLETED=$((TASKS_COMPLETED + 1))
  _update_status "running"

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
