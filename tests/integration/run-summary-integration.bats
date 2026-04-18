#!/usr/bin/env bats

load '../helpers/common'

setup() {
  setup_test_dir
}

teardown() {
  cleanup_test_dir
}

@test "summary on all-tasks-done exit (no tasks at start)" {
  mock_backlog "No tasks found"
  mock_tool opencode "done"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  [[ "$output" == *"Ralph Run Summary"* ]]
  [[ "$output" == *"Exit reason:        all tasks done"* ]]
  [[ "$output" == *"Tasks completed:    0"* ]]
}

@test "summary on completion signal" {
  mock_tool opencode '<promise>COMPLETE</promise>'
  mock_backlog "TASK-1 - Test task"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  [[ "$output" == *"Ralph Run Summary"* ]]
  [[ "$output" == *"Exit reason:        all tasks done"* ]]
  [[ "$output" == *"Tasks completed:    1"* ]]
  [[ "$output" == *"Iterations used:    1 of 3"* ]]
}

@test "summary on max iterations reached" {
  mock_tool opencode "iteration done"
  mock_backlog "TASK-1 - Test task"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 2
  [ "$status" -eq 1 ]
  [[ "$output" == *"Ralph Run Summary"* ]]
  [[ "$output" == *"Exit reason:        max iterations reached"* ]]
  [[ "$output" == *"Iterations used:    2 of 2"* ]]
}

@test "summary on error with on-error=stop" {
  mock_backlog "TASK-1 - Test task"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode --on-error stop 3
  [ "$status" -ne 0 ]
  [[ "$output" == *"Ralph Run Summary"* ]]
  [[ "$output" == *"Exit reason:        error"* ]]
  [[ "$output" == *"Failed iterations:  1"* ]]
}

@test "summary on error with on-error=continue tracks failures" {
  mock_backlog "TASK-1 - Test task"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode --on-error continue 2
  [ "$status" -eq 1 ]
  [[ "$output" == *"Ralph Run Summary"* ]]
  [[ "$output" == *"Exit reason:        max iterations reached"* ]]
  [[ "$output" == *"Failed iterations:  2"* ]]
  [[ "$output" == *"Tasks completed:    0"* ]]
}

@test "summary includes per-iteration durations" {
  mock_tool opencode '<promise>COMPLETE</promise>'
  mock_backlog "TASK-1 - Test task"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  [[ "$output" == *"Per-iteration durations:"* ]]
  [[ "$output" == *"Iteration 1:"* ]]
}

@test "summary on signal shows interrupted" {
  mock_backlog "TASK-1 - Test task"
  mkdir -p "$TEST_DIR/bin"
  local marker="$TEST_DIR/tool_started"
  cat > "$TEST_DIR/bin/opencode" <<MOCK
#!/bin/bash
touch "$marker"
sleep 3
MOCK
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"

  cd "$PROJECT_ROOT"
  bash ralph.sh --tool opencode 3 > "$TEST_DIR/signal_output.txt" 2>&1 &
  RALPH_PID=$!

  # Wait until the mock tool starts (up to 5s)
  for _ in $(seq 1 50); do
    if [[ -f "$marker" ]]; then break; fi
    sleep 0.1
  done

  kill -TERM "$RALPH_PID"
  wait "$RALPH_PID" 2>/dev/null || true

  output=$(cat "$TEST_DIR/signal_output.txt")
  [[ "$output" == *"Ralph Run Summary"* ]]
  [[ "$output" == *"Exit reason:        interrupted"* ]]
}
