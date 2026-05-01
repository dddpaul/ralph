#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PASS=0
FAIL=0

assert_eq() {
  local test_name="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "PASS: $test_name"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $test_name"
    echo "  expected: $expected"
    echo "  actual:   $actual"
    FAIL=$((FAIL + 1))
  fi
}

assert_contains() {
  local test_name="$1" expected="$2" actual="$3"
  if [[ "$actual" == *"$expected"* ]]; then
    echo "PASS: $test_name"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $test_name"
    echo "  expected substring: $expected"
    echo "  actual: $actual"
    FAIL=$((FAIL + 1))
  fi
}

setup() {
  FIXTURE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ralph-status-test.XXXXXX")
  mkdir -p "$FIXTURE_DIR/backlog"

  export RALPH_SOURCE_ONLY=1
  export RALPH_STATUS_FILE="$FIXTURE_DIR/backlog/.ralph-status.json"
  export RALPH_HEARTBEAT_FILE="$FIXTURE_DIR/backlog/.ralph-heartbeat"
  export RALPH_RUN_LOG="$FIXTURE_DIR/backlog/.ralph-run.log"

  # Source ralph.sh to get access to functions
  source "$SCRIPT_DIR/ralph.sh"

  # Set up required global state
  RUN_START_TIME=$(date +%s)
  RUN_STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  TASKS_DONE_IDS=""
  STATUS_ERRORS=""
  CURRENT_TASK=""
  LAST_ITER_DURATION=""
  CURRENT_ITERATION=0
  ITERATION_STARTED_AT=""
  MAX_ITERATIONS=10
  TOOL="claude"
  TIMEOUT=15
  TIMEOUT_SEC=900
  STATUS_FILE="$RALPH_STATUS_FILE"
  TASK_WHITELIST=()
}

teardown() {
  rm -rf "$FIXTURE_DIR"
}

# --- Test 1: Status file contains iteration_started_at ---
test_iteration_started_at_present() {
  setup
  CURRENT_ITERATION=1
  ITERATION_STARTED_AT="2026-04-30T12:00:00Z"
  _update_status "running"

  local content
  content=$(<"$STATUS_FILE")
  assert_contains "iteration_started_at in status" '"iteration_started_at":"2026-04-30T12:00:00Z"' "$content"
  teardown
}

# --- Test 2: iteration_started_at is null when not set ---
test_iteration_started_at_null() {
  setup
  ITERATION_STARTED_AT=""
  _update_status "running"

  local content
  content=$(<"$STATUS_FILE")
  assert_contains "iteration_started_at null when empty" '"iteration_started_at":null' "$content"
  teardown
}

# --- Test 3: timeout_sec in status ---
test_timeout_sec_present() {
  setup
  TIMEOUT_SEC=900
  _update_status "running"

  local content
  content=$(<"$STATUS_FILE")
  assert_contains "timeout_sec in status" '"timeout_sec":900' "$content"
  teardown
}

# --- Test 4: Structured errors with iteration/at/message ---
test_structured_errors() {
  setup
  CURRENT_ITERATION=2
  _append_status_error "Iteration 2 failed with exit code 1"
  _update_status "running"

  local content
  content=$(<"$STATUS_FILE")
  assert_contains "error has iteration field" '"iteration":2' "$content"
  assert_contains "error has at field" '"at":"' "$content"
  assert_contains "error has message field" '"message":"Iteration 2 failed with exit code 1"' "$content"
  teardown
}

# --- Test 5: Multiple structured errors ---
test_multiple_errors() {
  setup
  CURRENT_ITERATION=1
  _append_status_error "First error"
  CURRENT_ITERATION=2
  _append_status_error "Second error"
  _update_status "running"

  local content
  content=$(<"$STATUS_FILE")

  local error_count
  error_count=$(echo "$content" | grep -o '"message"' | wc -l)
  assert_eq "two error objects" "2" "$(echo "$error_count" | tr -d ' ')"
  assert_contains "first error message" '"message":"First error"' "$content"
  assert_contains "second error message" '"message":"Second error"' "$content"
  teardown
}

# --- Test 6: Empty errors is empty array ---
test_empty_errors() {
  setup
  STATUS_ERRORS=""
  _update_status "running"

  local content
  content=$(<"$STATUS_FILE")
  assert_contains "empty errors array" '"errors":[]' "$content"
  teardown
}

# --- Test 7: _status_json_raw_array with empty input ---
test_raw_array_empty() {
  local result
  result=$(_status_json_raw_array "")
  assert_eq "raw array empty" "[]" "$result"
}

# --- Test 8: _status_json_raw_array with single item ---
test_raw_array_single() {
  setup
  local result
  result=$(_status_json_raw_array '{"a":1}')
  assert_eq "raw array single" '[{"a":1}]' "$result"
  teardown
}

# --- Test 9: _status_json_raw_array with multiple items ---
test_raw_array_multiple() {
  setup
  local input=$'{"a":1}\n{"b":2}'
  local result
  result=$(_status_json_raw_array "$input")
  assert_eq "raw array multiple" '[{"a":1},{"b":2}]' "$result"
  teardown
}

# --- Test 10: Full status JSON is valid (parseable) ---
test_valid_json() {
  setup
  CURRENT_ITERATION=3
  ITERATION_STARTED_AT="2026-04-30T12:00:00Z"
  CURRENT_TASK="TASK-70"
  LAST_ITER_DURATION=120
  _append_status_error "test error"
  _update_status "running"

  local content
  content=$(<"$STATUS_FILE")

  if command -v python3 &>/dev/null; then
    if python3 -c "import json; json.loads('''$content''')" 2>/dev/null; then
      echo "PASS: valid JSON output"
      PASS=$((PASS + 1))
    else
      echo "FAIL: valid JSON output — not parseable"
      echo "  content: $content"
      FAIL=$((FAIL + 1))
    fi
  elif command -v node &>/dev/null; then
    if node -e "JSON.parse(\`$content\`)" 2>/dev/null; then
      echo "PASS: valid JSON output"
      PASS=$((PASS + 1))
    else
      echo "FAIL: valid JSON output — not parseable"
      echo "  content: $content"
      FAIL=$((FAIL + 1))
    fi
  else
    echo "SKIP: valid JSON output — no JSON parser available"
  fi
  teardown
}

# Run all tests
test_iteration_started_at_present
test_iteration_started_at_null
test_timeout_sec_present
test_structured_errors
test_multiple_errors
test_empty_errors
test_raw_array_empty
test_raw_array_single
test_raw_array_multiple
test_valid_json

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL)) tests"
[[ $FAIL -eq 0 ]] || exit 1
