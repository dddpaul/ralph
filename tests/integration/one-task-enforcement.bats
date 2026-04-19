#!/usr/bin/env bats
# Integration tests for one-task-per-iteration enforcement

load '../helpers/common'

setup() {
  setup_test_dir
}

teardown() {
  cleanup_test_dir
}

mock_opencode_output() {
  local output="$1"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<EOF
#!/bin/bash
cat <<'AGENT_OUTPUT'
$output
AGENT_OUTPUT
EOF
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
}

@test "Warning when agent outputs 0 Task Summary blocks" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_output "Some work done but no summary block"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 1

  [[ "$output" == *"WARNING: Iteration 1 produced 0 '## Task Summary' blocks (expected 1)"* ]]
}

@test "Warning when agent outputs 2 Task Summary blocks" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_output "First task done

## Task Summary

- **Task:** TASK-1

Second task done

## Task Summary

- **Task:** TASK-2"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 1

  [[ "$output" == *"WARNING: Iteration 1 produced 2 '## Task Summary' blocks (expected 1)"* ]]
}

@test "No warning when agent outputs exactly 1 Task Summary block" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_output "Task done

## Task Summary

- **Task:** TASK-1 — Test task"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 1

  [[ "$output" != *"WARNING"*"Task Summary"* ]]
}

@test "Warning when agent times out with 0 Task Summary blocks" {
  mock_backlog "TASK-1 - Test task"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'EOF'
#!/bin/bash
echo "Working on task but timed out before finishing"
exit 124
EOF
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 1

  [[ "$output" == *"WARNING: Iteration 1 produced 0 '## Task Summary' blocks (expected 1)"* ]]
}

@test "No warning when COMPLETE signal present with 0 blocks" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_output "All tasks are done.

<promise>COMPLETE</promise>"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 5

  [[ "$output" != *"WARNING"*"Task Summary"* ]]
}
