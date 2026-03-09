#!/usr/bin/env bats
# Integration tests for prompt generation

load '../helpers/common'

setup() {
  setup_test_dir
  MOCK_LOG="$TEST_DIR/mock-opencode.log"
}

teardown() {
  cleanup_test_dir
}

@test "Prompt contains MODE: autonomous" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_log "$MOCK_LOG"
  
  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode 1 2>&1 || true
  
  [[ -f "$MOCK_LOG" ]]
  grep -q "MODE: autonomous" "$MOCK_LOG"
}

@test "Prompt contains Task Lifecycle reference" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_log "$MOCK_LOG"
  
  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode 1 2>&1 || true
  
  [[ -f "$MOCK_LOG" ]]
  grep -q "Task Lifecycle" "$MOCK_LOG"
}

@test "Prompt contains ## Task Summary requirement" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_log "$MOCK_LOG"
  
  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode 1 2>&1 || true
  
  [[ -f "$MOCK_LOG" ]]
  grep -q "## Task Summary" "$MOCK_LOG"
}

@test "Iteration number included in prompt" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_log "$MOCK_LOG"
  
  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode 1 2>&1 || true
  
  [[ -f "$MOCK_LOG" ]]
  grep -q "iteration 1 of 1" "$MOCK_LOG"
}
