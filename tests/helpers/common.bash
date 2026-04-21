#!/usr/bin/env bash
# Common test helpers for ralph.sh tests

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"

# Source the main script for testing functions
RALPH_SCRIPT="$PROJECT_ROOT/ralph.sh"

# Create a temporary test directory
setup_test_dir() {
  TEST_DIR=$(mktemp -d)
  export TEST_DIR
  export RALPH_STATUS_FILE="$TEST_DIR/.ralph-status.json"
  export RALPH_RUN_LOG="$TEST_DIR/.ralph-run.log"
  export RALPH_HEARTBEAT_FILE="$TEST_DIR/.ralph-heartbeat"
}

# Cleanup temporary test directory
cleanup_test_dir() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

# Mock the backlog CLI
mock_backlog() {
  local response="$1"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/backlog" <<EOF
#!/bin/bash
echo "$response"
EOF
  chmod +x "$TEST_DIR/bin/backlog"
  export PATH="$TEST_DIR/bin:$PATH"
}

# Mock the devcontainer CLI
mock_devcontainer() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/devcontainer" <<EOF
#!/bin/bash
echo "Devcontainer mocked"
EOF
  chmod +x "$TEST_DIR/bin/devcontainer"
  export PATH="$TEST_DIR/bin:$PATH"
}

# Mock AI tools (claude, opencode)
mock_tool() {
  local tool="$1"
  local output="${2:-AI tool mocked}"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/$tool" <<EOF
#!/bin/bash
echo "$output"
EOF
  chmod +x "$TEST_DIR/bin/$tool"
  export PATH="$TEST_DIR/bin:$PATH"
}

# Create a fake backlog structure for testing
create_fake_backlog() {
  mkdir -p "$TEST_DIR/backlog/tasks"
  echo "# Task 1" > "$TEST_DIR/backlog/tasks/task-1.md"
}

# Mock opencode to capture arguments to a log file
# opencode receives prompt as argument (opencode run "$PROMPT"), not stdin
mock_opencode_with_log() {
  local log_file="$1"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<EOF
#!/bin/bash
echo "\$*" > "$log_file"
echo "Mocked"
EOF
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
}

# Mock backlog with per-status responses
# Usage: mock_backlog_multi "todo response" "done response" "in progress response"
mock_backlog_multi() {
  local todo_resp="$1"
  local done_resp="${2:-No tasks found}"
  local inprog_resp="${3:-No tasks found}"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/backlog" <<'OUTEREOF'
#!/bin/bash
prev=""
status=""
for arg in "$@"; do
  if [[ "$prev" == "-s" ]]; then
    status="$arg"
  fi
  prev="$arg"
done
OUTEREOF
  cat >> "$TEST_DIR/bin/backlog" <<EOF
case "\$status" in
  "Done") echo "$done_resp" ;;
  "In Progress") echo "$inprog_resp" ;;
  *) echo "$todo_resp" ;;
esac
EOF
  chmod +x "$TEST_DIR/bin/backlog"
  export PATH="$TEST_DIR/bin:$PATH"
}
