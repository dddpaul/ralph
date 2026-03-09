#!/usr/bin/env bats
# Integration tests for completion signal detection

load '../helpers/common'

setup() {
  setup_test_dir
}

teardown() {
  cleanup_test_dir
}

mock_opencode_with_completion() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'EOF'
#!/bin/bash
echo "Some output from opencode"
echo "<promise>COMPLETE</promise>"
echo "More output"
EOF
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
}

mock_opencode_without_completion() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'EOF'
#!/bin/bash
echo "Task completed successfully"
echo "Moving to next task"
EOF
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
}

@test "Script exits with code 0 on complete signal" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_completion
  
  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 5
  
  [ "$status" -eq 0 ]
}

@test "Ralph completed all tasks message printed" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_completion
  
  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 5
  
  [[ "$output" == *"Ralph completed all tasks!"* ]]
}

@test "Iteration count shown in completion message" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_completion
  
  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 5
  
  [[ "$output" == *"Completed at iteration"* ]]
  [[ "$output" == *"of 5"* ]]
}

@test "No completion signal when not present" {
  mock_backlog "TASK-1 - Test task
TASK-2 - Another task"
  mock_opencode_without_completion
  
  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 1
  
  [ "$status" -eq 1 ]
}

@test "Detects completion signal with surrounding text" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_completion
  
  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  
  [ "$status" -eq 0 ]
  [[ "$output" == *"Ralph completed all tasks!"* ]]
}
