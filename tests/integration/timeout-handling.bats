#!/usr/bin/env bats
# Integration tests for timeout handling

load '../helpers/common'

setup() {
  setup_test_dir
}

teardown() {
  cleanup_test_dir
}

mock_opencode_with_timeout() {
  local sleep_duration="$1"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<EOF
#!/bin/bash
echo "Opencode starting..."
sleep $sleep_duration
echo "Opencode finished (should not reach here if timeout works)"
echo "## Task Summary"
echo "- Task: TASK-1 - Test task"
echo "- What was implemented: Test"
echo "- Files changed: none"
echo "- Key decisions: none"
EOF
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
}

mock_opencode_normal() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'EOF'
#!/bin/bash
echo "Opencode running..."
sleep 0.5
echo "## Task Summary"
echo "- Task: TASK-1 - Test task"
echo "- What was implemented: Test"
echo "- Files changed: none"
echo "- Key decisions: none"
EOF
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
}

mock_backlog_with_counter() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/backlog" <<'SCRIPT'
#!/bin/bash
CALL_FILE="/tmp/backlog_calls_$$"
if [[ ! -f "$CALL_FILE" ]]; then
  echo "0" > "$CALL_FILE"
fi
CALLS=$(cat "$CALL_FILE")
CALLS=$((CALLS + 1))
echo "$CALLS" > "$CALL_FILE"

if [[ "$1" == "task" && "$2" == "list" ]]; then
  if [[ "$CALLS" -eq 1 ]]; then
    echo "TASK-1 - Test task"
    echo "TASK-2 - Another task"
  else
    echo "No tasks found"
  fi
else
  echo "backlog mocked"
fi
SCRIPT
  chmod +x "$TEST_DIR/bin/backlog"
  export PATH="$TEST_DIR/bin:$PATH"
}

@test "Timeout warning message printed when iteration times out" {
  mock_backlog_with_counter
  mock_opencode_with_timeout 90
  
  cd "$PROJECT_ROOT"
  run timeout 180 bash ralph.sh --tool opencode --timeout 1 2
  
  [[ "$output" == *"WARNING:"*"timed out"* ]]
}

@test "Script continues to next iteration after timeout" {
  mock_backlog_with_counter
  mock_opencode_with_timeout 90
  
  cd "$PROJECT_ROOT"
  run timeout 180 bash ralph.sh --tool opencode --timeout 1 2
  
  [[ "$output" == *"Iteration 1 of 2"* ]]
  [[ "$output" == *"Iteration 2 of 2"* ]]
}

@test "Exit code 124 handled correctly" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_timeout 90
  
  cd "$PROJECT_ROOT"
  run timeout 180 bash ralph.sh --tool opencode --timeout 1 1
  
  [[ "$output" == *"WARNING:"*"timed out"* ]]
}

@test "Normal execution when no timeout occurs" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_normal
  
  cd "$PROJECT_ROOT"
  run timeout 30 bash ralph.sh --tool opencode --timeout 1 1
  
  [[ "$output" != *"WARNING:"*"timed out"* ]]
  [[ "$output" == *"Iteration 1 of 1"* ]]
}

@test "Timeout with completion signal still stops loop" {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'EOF'
#!/bin/bash
echo "Starting task..."
echo "<promise>COMPLETE</promise>"
echo "After completion"
EOF
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
  
  mock_backlog "TASK-1 - Test task"
  
  cd "$PROJECT_ROOT"
  run timeout 30 bash ralph.sh --tool opencode --timeout 1 1
  
  [ "$status" -eq 0 ]
  [[ "$output" == *"Ralph completed all tasks!"* ]]
}

@test "Multiple timeouts handled gracefully" {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/backlog" <<'SCRIPT'
#!/bin/bash
CALL_FILE="/tmp/backlog_multi_calls_$$"
if [[ ! -f "$CALL_FILE" ]]; then
  echo "0" > "$CALL_FILE"
fi
CALLS=$(cat "$CALL_FILE")
CALLS=$((CALLS + 1))
echo "$CALLS" > "$CALL_FILE"

if [[ "$1" == "task" && "$2" == "list" ]]; then
  if [[ "$CALLS" -le 3 ]]; then
    echo "TASK-1 - Test task"
    echo "TASK-2 - Another task"
    echo "TASK-3 - Third task"
  else
    echo "No tasks found"
  fi
fi
SCRIPT
  chmod +x "$TEST_DIR/bin/backlog"
  export PATH="$TEST_DIR/bin:$PATH"
  
  mock_opencode_with_timeout 90
  
  cd "$PROJECT_ROOT"
  run timeout 300 bash ralph.sh --tool opencode --timeout 1 3
  
  [[ "$output" == *"Iteration 1 of 3"* ]]
  [[ "$output" == *"Iteration 2 of 3"* ]]
  [[ "$output" == *"Iteration 3 of 3"* ]]
  [[ "$output" == *"WARNING:"*"timed out"* ]]
}

@test "Invalid timeout value rejected" {
  cd "$PROJECT_ROOT"
  run timeout 5 bash ralph.sh --tool opencode --timeout 0 1
  
  [ "$status" -eq 1 ]
  [[ "$output" == *"Timeout must be"* ]]
}

@test "Fractional timeout value rejected" {
  cd "$PROJECT_ROOT"
  run timeout 5 bash ralph.sh --tool opencode --timeout 0.5 1
  
  [ "$status" -eq 1 ]
  [[ "$output" == *"Timeout must be"* ]]
}

@test "Temp file cleaned up on normal exit" {
  mock_backlog_with_counter
  mock_opencode_normal
  
  mkdir -p "$TEST_DIR/tmpfiles"
  export TMPDIR="$TEST_DIR/tmpfiles"
  
  cd "$PROJECT_ROOT"
  run timeout 30 bash ralph.sh --tool opencode --timeout 1 1
  
  local tmp_count
  tmp_count=$(find "$TEST_DIR/tmpfiles" -type f 2>/dev/null | wc -l)
  [ "$tmp_count" -eq 0 ]
}

@test "Temp file cleaned up on timeout" {
  mock_backlog_with_counter
  mock_opencode_with_timeout 90
  
  mkdir -p "$TEST_DIR/tmpfiles"
  export TMPDIR="$TEST_DIR/tmpfiles"
  
  cd "$PROJECT_ROOT"
  run timeout 180 bash ralph.sh --tool opencode --timeout 1 2
  
  local tmp_count
  tmp_count=$(find "$TEST_DIR/tmpfiles" -type f 2>/dev/null | wc -l)
  [ "$tmp_count" -eq 0 ]
}

@test "Temp file cleaned up on error" {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/backlog" <<'SCRIPT'
#!/bin/bash
echo "TASK-1 - Test task"
SCRIPT
  chmod +x "$TEST_DIR/bin/backlog"
  
  cat > "$TEST_DIR/bin/opencode" <<'SCRIPT'
#!/bin/bash
echo "Failing..."
exit 1
SCRIPT
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
  
  mkdir -p "$TEST_DIR/tmpfiles"
  export TMPDIR="$TEST_DIR/tmpfiles"
  
  cd "$PROJECT_ROOT"
  run timeout 30 bash ralph.sh --tool opencode --timeout 1 1 --on-error stop
  
  [ "$status" -eq 1 ]
  local tmp_count
  tmp_count=$(find "$TEST_DIR/tmpfiles" -type f 2>/dev/null | wc -l)
  [ "$tmp_count" -eq 0 ]
}
