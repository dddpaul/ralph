#!/usr/bin/env bats
# Unit tests for dependency checking in ralph.sh

load '../helpers/common'

setup() {
  setup_test_dir
}

teardown() {
  cleanup_test_dir
}

@test "Missing backlog CLI produces error exit code 1" {
  # Remove backlog from PATH by using minimal PATH
  run bash -c "
    export PATH='/usr/bin:/bin'
    source '$RALPH_SCRIPT' 2>&1
  " || true
  
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"backlog"* ]] || [[ "$output" == *"not found"* ]]
}

@test "Missing backlog CLI shows installation message" {
  run bash -c "
    export PATH='/usr/bin:/bin'
    source '$RALPH_SCRIPT' 2>&1
  " || true
  
  [[ "$output" == *"Install from"* ]] || [[ "$output" == *"github.com/MrLesk/Backlog.md"* ]]
}

@test "Missing opencode CLI produces appropriate error" {
  # Mock backlog but not opencode
  mock_backlog "No tasks found"
  
  run bash -c "
    export PATH='$TEST_DIR/bin:/usr/bin:/bin'
    source '$RALPH_SCRIPT' --tool opencode 2>&1
  " || true
  
  # Script should fail when trying to run opencode
  [[ "$output" == *"opencode"* ]] || [[ "$output" == *"not found"* ]] || [[ "$status" -ne 0 ]]
}

@test "Missing devcontainer CLI handled when --devcontainer used" {
  # Mock backlog but not devcontainer
  mock_backlog "No tasks found"
  
  run bash -c "
    export PATH='$TEST_DIR/bin:/usr/bin:/bin'
    source '$RALPH_SCRIPT' --devcontainer 2>&1
  " || true
  
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"devcontainer"* ]] || [[ "$output" == *"not found"* ]]
}

@test "Missing devcontainer CLI shows installation instructions" {
  mock_backlog "No tasks found"
  
  run bash -c "
    export PATH='$TEST_DIR/bin:/usr/bin:/bin'
    source '$RALPH_SCRIPT' --devcontainer 2>&1
  " || true
  
  [[ "$output" == *"npm install"* ]] || [[ "$output" == *"@devcontainers/cli"* ]]
}

@test "All dependencies present allows script to proceed" {
  # Mock all dependencies
  mock_backlog "No tasks found"
  mock_tool "opencode" "opencode mocked"
  
  run bash -c "
    export PATH='$TEST_DIR/bin:$PATH'
    timeout 2 bash '$RALPH_SCRIPT' --tool opencode 1 2>&1 || true
  "
  
  # Script should at least start (not fail on dependency check)
  [[ "$output" == *"Ralph"* ]] || [[ "$output" == *"Starting"* ]] || [[ "$output" == *"No tasks found"* ]]
}

@test "Mock PATH to simulate missing dependencies" {
  # Test that PATH manipulation works correctly
  mkdir -p "$TEST_DIR/bin"
  
  # Create a script that checks for a fake command
  cat > "$TEST_DIR/check_deps.sh" <<'EOF'
#!/bin/bash
if ! command -v fake_command &> /dev/null; then
  echo "Error: 'fake_command' not found"
  exit 1
fi
EOF
  chmod +x "$TEST_DIR/check_deps.sh"
  
  run bash "$TEST_DIR/check_deps.sh"
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"fake_command"* ]]
  
  # Now add the fake command to PATH
  cat > "$TEST_DIR/bin/fake_command" <<'EOF'
#!/bin/bash
echo "fake command found"
EOF
  chmod +x "$TEST_DIR/bin/fake_command"
  
  export PATH="$TEST_DIR/bin:$PATH"
  run bash "$TEST_DIR/check_deps.sh"
  [[ "$status" -eq 0 ]]
}
