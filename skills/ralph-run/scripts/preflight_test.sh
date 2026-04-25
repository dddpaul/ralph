#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PREFLIGHT="$SCRIPT_DIR/preflight.sh"
PASS=0
FAIL=0

SYS_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

setup_fixture() {
  FIXTURE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/preflight-test.XXXXXX")
  mkdir -p "$FIXTURE_DIR/backlog"
  RALPH_SH="$FIXTURE_DIR/ralph.sh"
  cat > "$RALPH_SH" <<'SCRIPTEOF'
#!/bin/bash
echo "hello"
SCRIPTEOF
  chmod +x "$RALPH_SH"
}

teardown_fixture() {
  rm -rf "$FIXTURE_DIR"
}

run_preflight() {
  local dir="$1" path="$2" ralph="$3" devcontainer="$4"
  cd "$dir" && PATH="$path" bash "$PREFLIGHT" "$ralph" "$devcontainer" 2>/dev/null
}

assert_error() {
  local test_name="$1"
  local expected_substr="$2"
  local output="$3"
  local exit_code="$4"

  if [[ $exit_code -eq 0 ]]; then
    echo "FAIL: $test_name — expected non-zero exit, got 0"
    echo "  output: $output"
    FAIL=$((FAIL + 1))
    return
  fi
  if [[ "$output" != ERROR:* ]]; then
    echo "FAIL: $test_name — output does not start with 'ERROR:'"
    echo "  output: $output"
    FAIL=$((FAIL + 1))
    return
  fi
  if [[ "$output" != *"$expected_substr"* ]]; then
    echo "FAIL: $test_name — expected substring '$expected_substr' not found"
    echo "  output: $output"
    FAIL=$((FAIL + 1))
    return
  fi
  local line_count
  line_count=$(echo "$output" | wc -l)
  if [[ $line_count -ne 1 ]]; then
    echo "FAIL: $test_name — expected exactly 1 line, got $line_count"
    echo "  output: $output"
    FAIL=$((FAIL + 1))
    return
  fi
  echo "PASS: $test_name"
  PASS=$((PASS + 1))
}

assert_ok() {
  local test_name="$1"
  local output="$2"
  local exit_code="$3"

  if [[ $exit_code -ne 0 ]]; then
    echo "FAIL: $test_name — expected exit 0, got $exit_code"
    echo "  output: $output"
    FAIL=$((FAIL + 1))
    return
  fi
  if [[ "$output" != OK\ RALPH_PATH=* ]]; then
    echo "FAIL: $test_name — output does not match 'OK RALPH_PATH=...'"
    echo "  output: $output"
    FAIL=$((FAIL + 1))
    return
  fi
  local line_count
  line_count=$(echo "$output" | wc -l)
  if [[ $line_count -ne 1 ]]; then
    echo "FAIL: $test_name — expected exactly 1 line, got $line_count"
    echo "  output: $output"
    FAIL=$((FAIL + 1))
    return
  fi
  echo "PASS: $test_name"
  PASS=$((PASS + 1))
}

make_mock_backlog() {
  local fixture_dir="$1"
  local response="$2"
  mkdir -p "$fixture_dir/backlog-bin"
  cat > "$fixture_dir/backlog-bin/backlog" <<MOCKEOF
#!/bin/bash
$response
MOCKEOF
  chmod +x "$fixture_dir/backlog-bin/backlog"
}

TODO_RESPONSE='echo "To Do:"; echo "  TASK-1 - Something"'
NO_TODO_RESPONSE='echo "No tasks found"'

# --- Test 1: No To Do tasks → ERROR ---
test_no_todo_tasks() {
  setup_fixture
  make_mock_backlog "$FIXTURE_DIR" "$NO_TODO_RESPONSE"

  local output exit_code
  output=$(run_preflight "$FIXTURE_DIR" "$FIXTURE_DIR/backlog-bin:$SYS_PATH" "$RALPH_SH" false)
  exit_code=$?
  assert_error "no To Do tasks" "No To Do tasks" "$output" "$exit_code"
  teardown_fixture
}

# --- Test 2: Ralph already running (fresh heartbeat) → ERROR ---
test_ralph_running() {
  setup_fixture
  cat > "$FIXTURE_DIR/backlog/.ralph-status.json" <<'STATUSEOF'
{"pid":99999,"state":"running"}
STATUSEOF
  touch "$FIXTURE_DIR/backlog/.ralph-heartbeat"
  make_mock_backlog "$FIXTURE_DIR" "$TODO_RESPONSE"

  local output exit_code
  output=$(run_preflight "$FIXTURE_DIR" "$FIXTURE_DIR/backlog-bin:$SYS_PATH" "$RALPH_SH" false)
  exit_code=$?
  assert_error "ralph already running" "already running" "$output" "$exit_code"
  teardown_fixture
}

# --- Test 3: devcontainer=true with missing CLI → ERROR ---
test_devcontainer_missing() {
  setup_fixture
  make_mock_backlog "$FIXTURE_DIR" "$TODO_RESPONSE"

  local output exit_code
  output=$(run_preflight "$FIXTURE_DIR" "$FIXTURE_DIR/backlog-bin:$SYS_PATH" "$RALPH_SH" true)
  exit_code=$?
  assert_error "devcontainer CLI missing" "devcontainer CLI not found" "$output" "$exit_code"
  teardown_fixture
}

# --- Test 4: ralph.sh not executable → ERROR ---
test_not_executable() {
  setup_fixture
  chmod -x "$RALPH_SH"
  make_mock_backlog "$FIXTURE_DIR" "$TODO_RESPONSE"

  local output exit_code
  output=$(run_preflight "$FIXTURE_DIR" "$FIXTURE_DIR/backlog-bin:$SYS_PATH" "$RALPH_SH" false)
  exit_code=$?
  assert_error "ralph.sh not executable" "not executable" "$output" "$exit_code"
  teardown_fixture
}

# --- Test 5: ralph.sh syntax error → ERROR ---
test_syntax_error() {
  setup_fixture
  cat > "$RALPH_SH" <<'BADEOF'
#!/bin/bash
echo "unterminated
BADEOF
  chmod +x "$RALPH_SH"
  make_mock_backlog "$FIXTURE_DIR" "$TODO_RESPONSE"

  local output exit_code
  output=$(run_preflight "$FIXTURE_DIR" "$FIXTURE_DIR/backlog-bin:$SYS_PATH" "$RALPH_SH" false)
  exit_code=$?
  assert_error "ralph.sh syntax error" "syntax errors" "$output" "$exit_code"
  teardown_fixture
}

# --- Test 6: Valid setup → OK ---
test_valid_setup() {
  setup_fixture
  make_mock_backlog "$FIXTURE_DIR" "$TODO_RESPONSE"

  local output exit_code
  output=$(run_preflight "$FIXTURE_DIR" "$FIXTURE_DIR/backlog-bin:$SYS_PATH" "$RALPH_SH" false)
  exit_code=$?
  assert_ok "valid setup" "$output" "$exit_code"
  teardown_fixture
}

# Run all tests
test_no_todo_tasks
test_ralph_running
test_devcontainer_missing
test_not_executable
test_syntax_error
test_valid_setup

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL)) tests"
[[ $FAIL -eq 0 ]] || exit 1
