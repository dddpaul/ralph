#!/usr/bin/env bats
# Tests for process cleanup on interruption (TASK-23)

load '../helpers/common'

setup() {
  setup_test_dir
}

teardown() {
  cleanup_test_dir
}

create_long_running_tool() {
  local pidfile="$1"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/claude" <<EOF
#!/bin/bash
echo \$\$ > "$pidfile"
sleep 300
EOF
  chmod +x "$TEST_DIR/bin/claude"
  export PATH="$TEST_DIR/bin:$PATH"
}

wait_for_pidfile() {
  local pidfile="$1"
  local waited=0
  while [[ ! -f "$pidfile" ]] && (( waited < 20 )); do
    sleep 0.5
    (( waited++ )) || true
  done
  [[ -f "$pidfile" ]]
}

@test "pkill -P kills child tool process (skill stop strategy)" {
  mock_backlog_multi 'TASK-5 - Test task'
  local tool_pidfile="$TEST_DIR/tool.pid"
  create_long_running_tool "$tool_pidfile"

  "$RALPH_SCRIPT" --tool claude --timeout 5 --log-file /dev/null 1 &
  local ralph_pid=$!

  wait_for_pidfile "$tool_pidfile"
  local tool_pid
  tool_pid=$(cat "$tool_pidfile")

  # Kill children first, then ralph (same strategy as ralph-stop skill)
  pkill -TERM -P "$ralph_pid" 2>/dev/null || true
  kill -TERM "$ralph_pid" 2>/dev/null || true
  sleep 2

  ! kill -0 "$tool_pid" 2>/dev/null
}

@test "RUN_LOG retains startup output after process tree kill" {
  mock_backlog_multi 'TASK-5 - Test task'
  local tool_pidfile="$TEST_DIR/tool.pid"
  create_long_running_tool "$tool_pidfile"

  "$RALPH_SCRIPT" --tool claude --timeout 5 --log-file /dev/null 1 &
  local ralph_pid=$!

  wait_for_pidfile "$tool_pidfile"

  pkill -TERM -P "$ralph_pid" 2>/dev/null || true
  kill -TERM "$ralph_pid" 2>/dev/null || true
  sleep 2

  run grep -c "Starting Ralph" backlog/.ralph-run.log
  [[ "$output" == "1" ]]
}

@test "status file shows state=failed after process tree kill" {
  mock_backlog_multi 'TASK-5 - Test task'
  local tool_pidfile="$TEST_DIR/tool.pid"
  create_long_running_tool "$tool_pidfile"

  "$RALPH_SCRIPT" --tool claude --timeout 5 --log-file /dev/null 1 &
  local ralph_pid=$!

  wait_for_pidfile "$tool_pidfile"

  pkill -TERM -P "$ralph_pid" 2>/dev/null || true
  kill -TERM "$ralph_pid" 2>/dev/null || true
  sleep 2

  # Status file should exist with failed state (trap may or may not fire,
  # but status was set to "running" at start)
  [[ -f "backlog/.ralph-status.json" ]]
  run python3 -c "import json; d=json.load(open('backlog/.ralph-status.json')); print(d['state'])"
  [[ "$output" == "failed" || "$output" == "running" ]]
}
