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

@test "--prompt-file loads prompt body from file" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_log "$MOCK_LOG"

  echo "Custom prompt from file." > "$TEST_DIR/custom-prompt.txt"

  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode --prompt-file "$TEST_DIR/custom-prompt.txt" 1 2>&1 || true

  [[ -f "$MOCK_LOG" ]]
  grep -q "Custom prompt from file." "$MOCK_LOG"
}

@test "--prompt-file still prepends MODE_PREFIX" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_log "$MOCK_LOG"

  echo "Custom prompt body." > "$TEST_DIR/custom-prompt.txt"

  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode --prompt-file "$TEST_DIR/custom-prompt.txt" 1 2>&1 || true

  [[ -f "$MOCK_LOG" ]]
  grep -q "MODE: autonomous" "$MOCK_LOG"
}

@test "Without --prompt-file, default prompt is used" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_log "$MOCK_LOG"

  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode 1 2>&1 || true

  [[ -f "$MOCK_LOG" ]]
  grep -q "Task Lifecycle" "$MOCK_LOG"
  grep -q "## Task Summary" "$MOCK_LOG"
}

@test "--prompt-file with non-existent file exits with error" {
  mock_backlog "TASK-1 - Test task"

  cd "$PROJECT_ROOT"
  run timeout 5 bash ralph.sh --tool opencode --prompt-file "/tmp/nonexistent-ralph-$$" 1 2>&1

  [[ "$status" -ne 0 ]]
  [[ "$output" == *"does not exist or is not readable"* ]]
}

@test "--prompt-file=path syntax works" {
  mock_backlog "TASK-1 - Test task"
  mock_opencode_with_log "$MOCK_LOG"

  echo "Equals syntax prompt." > "$TEST_DIR/eq-prompt.txt"

  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode "--prompt-file=$TEST_DIR/eq-prompt.txt" 1 2>&1 || true

  [[ -f "$MOCK_LOG" ]]
  grep -q "Equals syntax prompt." "$MOCK_LOG"
}

@test "--tasks sends targeted prompt with task ID" {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/backlog" <<'MOCKEOF'
#!/bin/bash
if [[ "$1" == "task" && "$2" == "42" ]]; then
  echo "Task TASK-42 - Whitelist test"
  echo "Status: ○ To Do"
elif [[ "$1" == "task" && "$2" == "list" ]]; then
  for arg in "$@"; do
    if [[ "$prev" == "-s" ]]; then
      if [[ "$arg" == "Done" ]]; then echo "No tasks found"; exit 0; fi
      if [[ "$arg" == "In Progress" ]]; then echo "No tasks found"; exit 0; fi
    fi
    prev="$arg"
  done
  echo "To Do:"
  echo "  TASK-42 - Whitelist test"
fi
MOCKEOF
  chmod +x "$TEST_DIR/bin/backlog"
  export PATH="$TEST_DIR/bin:$PATH"
  mock_opencode_with_log "$MOCK_LOG"

  cd "$PROJECT_ROOT"
  timeout 5 bash ralph.sh --tool opencode --tasks 42 1 2>&1 || true

  [[ -f "$MOCK_LOG" ]]
  grep -q "Execute TASK-42" "$MOCK_LOG"
  grep -q "Do NOT pick any other task" "$MOCK_LOG"
}
