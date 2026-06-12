#!/bin/bash
set -uo pipefail

usage() {
  echo "Usage: preflight.sh <ralph_path> <devcontainer:true|false> [--verbose] [--tasks <ids>] [--block-end-buffer-min <N>]"
  exit 1
}

VERBOSE=false
TASKS_RAW=""
BLOCK_END_BUFFER_MIN=0
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --verbose) VERBOSE=true; shift ;;
    --tasks) TASKS_RAW="$2"; shift 2 ;;
    --tasks=*) TASKS_RAW="${1#*=}"; shift ;;
    --block-end-buffer-min) BLOCK_END_BUFFER_MIN="$2"; shift 2 ;;
    --block-end-buffer-min=*) BLOCK_END_BUFFER_MIN="${1#*=}"; shift ;;
    *) POSITIONAL+=("$1"); shift ;;
  esac
done

[[ ${#POSITIONAL[@]} -ne 2 ]] && usage

RALPH_PATH="${POSITIONAL[0]}"
DEVCONTAINER="${POSITIONAL[1]}"

[[ "$DEVCONTAINER" != "true" && "$DEVCONTAINER" != "false" ]] && usage

verbose() {
  if [[ "$VERBOSE" == "true" ]]; then
    echo "$1"
  fi
}

# Check 1: To Do tasks exist (or validate --tasks whitelist)
if [[ -n "$TASKS_RAW" ]]; then
  if ! [[ "$TASKS_RAW" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
    verbose "check tasks_whitelist: FAIL (non-numeric)"
    echo "ERROR: --tasks must be comma-separated numeric IDs. Got: '$TASKS_RAW'"
    exit 1
  fi
  IFS=',' read -ra _WL_IDS <<< "$TASKS_RAW"
  for _wl_id in "${_WL_IDS[@]}"; do
    _wl_out=$(backlog task "$_wl_id" --plain 2>/dev/null)
    if [[ -z "$_wl_out" ]] || echo "$_wl_out" | grep -qE "^Task [0-9]+ not found\.$"; then
      verbose "check tasks_whitelist: FAIL (TASK-$_wl_id not found)"
      echo "ERROR: TASK-$_wl_id not found in backlog"
      exit 1
    fi
    _wl_status=$(echo "$_wl_out" | grep -o "Status:.*" | sed 's/Status:[[:space:]]*//' | sed 's/^[^[:alpha:]]*//')
    if [[ "$_wl_status" != *"To Do"* ]]; then
      verbose "check tasks_whitelist: FAIL (TASK-$_wl_id status: $_wl_status)"
      echo "ERROR: TASK-$_wl_id is not To Do (status: $_wl_status)"
      exit 1
    fi
  done
  verbose "check tasks_whitelist: ok (${#_WL_IDS[@]} tasks)"
else
  TODO_OUTPUT=$(backlog task list -s "To Do" --plain 2>/dev/null)
  if echo "$TODO_OUTPUT" | grep -q "No tasks found" || ! echo "$TODO_OUTPUT" | grep -q "TASK-"; then
    verbose "check todo_tasks: FAIL (no To Do tasks)"
    echo "ERROR: No To Do tasks in backlog"
    exit 1
  fi
  TODO_COUNT=$(echo "$TODO_OUTPUT" | grep -c "TASK-")
  verbose "check todo_tasks: ok ($TODO_COUNT tasks)"
fi

# Check 2: Ralph not already running
STATUS_FILE="backlog/.ralph-status.json"
if [[ -f "$STATUS_FILE" ]]; then
  STATE=$(grep -o '"state":"[^"]*"' "$STATUS_FILE" | grep -o '"[^"]*"$' | tr -d '"')
  if [[ "$STATE" == "running" ]]; then
    HB_FILE="backlog/.ralph-heartbeat"
    if [[ -f "$HB_FILE" ]]; then
      HB_MTIME=$(stat -c %Y "$HB_FILE" 2>/dev/null || stat -f %m "$HB_FILE" 2>/dev/null)
      NOW=$(date +%s)
      if [[ $(( NOW - HB_MTIME )) -lt 15 ]]; then
        PID=$(grep -o '"pid":[0-9]*' "$STATUS_FILE" | grep -o '[0-9]*')
        verbose "check ralph_running: FAIL (PID ${PID:-unknown} active)"
        echo "ERROR: Ralph is already running (PID ${PID:-unknown})"
        exit 1
      fi
    fi
  fi
fi
verbose "check ralph_running: ok (no fresh heartbeat)"

# Check 3: devcontainer CLI (only when devcontainer=true)
if [[ "$DEVCONTAINER" == "true" ]]; then
  if ! command -v devcontainer >/dev/null 2>&1; then
    verbose "check devcontainer_cli: FAIL (not found)"
    echo "ERROR: devcontainer CLI not found but devcontainer=true"
    exit 1
  fi
  verbose "check devcontainer_cli: ok"
else
  verbose "check devcontainer_cli: ok (skipped, devcontainer=false)"
fi

# Check 4: ralph.sh is executable
if [[ ! -x "$RALPH_PATH" ]]; then
  verbose "check ralph_executable: FAIL ($RALPH_PATH)"
  echo "ERROR: ralph.sh is not executable at $RALPH_PATH"
  exit 1
fi
verbose "check ralph_executable: ok"

# Check 5: ralph.sh has valid syntax
SYNTAX_ERR=$(mktemp "${TMPDIR:-/tmp}/preflight.XXXXXX")
if ! bash -n "$RALPH_PATH" 2>"$SYNTAX_ERR"; then
  MSG=$(grep -v 'warning: setlocale' "$SYNTAX_ERR" | head -1)
  rm -f "$SYNTAX_ERR"
  verbose "check ralph_syntax: FAIL"
  echo "ERROR: ralph.sh has syntax errors: $MSG"
  exit 1
fi
rm -f "$SYNTAX_ERR"
verbose "check ralph_syntax: ok"

# Check 6: usage cap (block-end buffer). Only invoke when BUFFER_MIN > 0.
if ! [[ "$BLOCK_END_BUFFER_MIN" =~ ^[0-9]+$ ]]; then
  verbose "check block_end_buffer: FAIL (non-integer: $BLOCK_END_BUFFER_MIN)"
  echo "ERROR: --block-end-buffer-min must be a non-negative integer. Got: '$BLOCK_END_BUFFER_MIN'"
  exit 1
fi
if [[ "$BLOCK_END_BUFFER_MIN" -gt 0 ]]; then
  USAGE_CHECK_SCRIPT="${RALPH_USAGE_CHECK_SCRIPT:-$(dirname "$0")/usage-check.sh}"
  USAGE_DISABLED_FLAG="${RALPH_USAGE_DISABLED_FLAG:-backlog/.ralph-usage-check-disabled}"
  if [[ ! -x "$USAGE_CHECK_SCRIPT" ]]; then
    verbose "check usage_check_script: FAIL ($USAGE_CHECK_SCRIPT)"
    echo "ERROR: usage-check.sh not found or not executable at $USAGE_CHECK_SCRIPT"
    exit 1
  fi
  _uc_out=$("$USAGE_CHECK_SCRIPT" "$BLOCK_END_BUFFER_MIN" 2>/dev/null)
  _uc_rc=$?
  case "$_uc_rc" in
    0)
      verbose "check usage: ok (block boundary outside ${BLOCK_END_BUFFER_MIN}m buffer)"
      ;;
    1)
      verbose "check usage: FAIL ($_uc_out)"
      echo "ERROR: usage cap tripped — $_uc_out"
      exit 1
      ;;
    2)
      verbose "check usage: WARN (cannot measure — block-end check disabled this run)"
      echo "WARNING: usage-check.sh cannot measure block boundary — continuing without block-end protection" >&2
      mkdir -p "$(dirname "$USAGE_DISABLED_FLAG")" 2>/dev/null
      : > "$USAGE_DISABLED_FLAG"
      ;;
    *)
      verbose "check usage: WARN (unexpected exit $_uc_rc — continuing)"
      ;;
  esac
else
  verbose "check usage: ok (skipped, buffer=0)"
fi

echo "OK RALPH_PATH=$RALPH_PATH"
