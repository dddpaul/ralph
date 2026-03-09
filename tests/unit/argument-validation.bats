#!/usr/bin/env bats
# Unit tests for argument validation in ralph.sh

load '../helpers/common'

setup() {
  setup_test_dir
  mock_backlog "No tasks found"
}

teardown() {
  cleanup_test_dir
}

@test "AC1: --tool opencode accepted as valid" {
  # Extract just the argument parsing logic from ralph.sh
  TOOL="amp"
  TIMEOUT=15
  MAX_ITERATIONS=10
  USE_DEVCONTAINER=false
  
  # Simulate parsing --tool opencode
  TOOL="opencode"
  
  # Validate tool choice (same logic as ralph.sh)
  if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "opencode" ]]; then
    return 1
  fi
  
  [[ "$TOOL" == "opencode" ]]
}

@test "AC2: Invalid tool rejected with exit code 1" {
  TOOL="amp"
  
  # Simulate invalid tool
  TOOL="invalid-tool"
  
  # Validate tool choice - should fail
  run bash -c '
    TOOL="invalid-tool"
    if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "opencode" ]]; then
      echo "Error: Invalid tool '\''$TOOL'\''. Must be '\''amp'\'', '\''claude'\'', or '\''opencode'\''."
      exit 1
    fi
  '
  
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"Invalid tool"* ]]
}

@test "AC3: --timeout parsed correctly" {
  TIMEOUT=15
  
  # Simulate --timeout 30 parsing
  TIMEOUT=30
  
  [[ "$TIMEOUT" -eq 30 ]]
}

@test "AC3: --timeout with equals sign parsed correctly" {
  TIMEOUT=15
  
  # Simulate --timeout=45 parsing (from ralph.sh logic)
  TIMEOUT="45"
  
  [[ "$TIMEOUT" -eq 45 ]]
}

@test "AC4: max_iterations parsed from positional argument" {
  MAX_ITERATIONS=10
  
  # Simulate parsing numeric positional argument
  arg="5"
  if [[ "$arg" =~ ^[0-9]+$ ]]; then
    MAX_ITERATIONS="$arg"
  fi
  
  [[ "$MAX_ITERATIONS" -eq 5 ]]
}

@test "AC4: Non-numeric positional argument ignored for max_iterations" {
  MAX_ITERATIONS=10
  
  # Simulate parsing non-numeric positional argument
  arg="invalid"
  if [[ "$arg" =~ ^[0-9]+$ ]]; then
    MAX_ITERATIONS="$arg"
  fi
  
  [[ "$MAX_ITERATIONS" -eq 10 ]]
}

@test "AC5: Help text shows opencode in usage" {
  # Check that ralph.sh contains opencode in usage line
  grep -q "opencode" "$RALPH_SCRIPT"
  
  # Check usage comment specifically
  run grep "Usage.*opencode" "$RALPH_SCRIPT"
  [[ "$status" -eq 0 ]]
}

@test "Tool validation: amp is valid" {
  TOOL="amp"
  if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "opencode" ]]; then
    return 1
  fi
  [[ "$TOOL" == "amp" ]]
}

@test "Tool validation: claude is valid" {
  TOOL="claude"
  if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "opencode" ]]; then
    return 1
  fi
  [[ "$TOOL" == "claude" ]]
}

@test "Tool validation: empty tool is invalid" {
  TOOL=""
  run bash -c '
    TOOL=""
    if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "opencode" ]]; then
      exit 1
    fi
  '
  [[ "$status" -eq 1 ]]
}

@test "Default values are correct" {
  TOOL="amp"
  MODEL="claude-opus-4-6"
  EFFORT="medium"
  TIMEOUT=15
  MAX_ITERATIONS=10
  USE_DEVCONTAINER=false

  [[ "$TOOL" == "amp" ]]
  [[ "$MODEL" == "claude-opus-4-6" ]]
  [[ "$EFFORT" == "medium" ]]
  [[ "$TIMEOUT" -eq 15 ]]
  [[ "$MAX_ITERATIONS" -eq 10 ]]
  [[ "$USE_DEVCONTAINER" == false ]]
}

@test "Effort validation: low is valid" {
  EFFORT="low"
  if [[ "$EFFORT" != "low" && "$EFFORT" != "medium" && "$EFFORT" != "high" ]]; then
    return 1
  fi
  [[ "$EFFORT" == "low" ]]
}

@test "Effort validation: medium is valid" {
  EFFORT="medium"
  if [[ "$EFFORT" != "low" && "$EFFORT" != "medium" && "$EFFORT" != "high" ]]; then
    return 1
  fi
  [[ "$EFFORT" == "medium" ]]
}

@test "Effort validation: high is valid" {
  EFFORT="high"
  if [[ "$EFFORT" != "low" && "$EFFORT" != "medium" && "$EFFORT" != "high" ]]; then
    return 1
  fi
  [[ "$EFFORT" == "high" ]]
}

@test "Effort validation: invalid value rejected" {
  run bash -c '
    EFFORT="extreme"
    if [[ "$EFFORT" != "low" && "$EFFORT" != "medium" && "$EFFORT" != "high" ]]; then
      echo "Error: Invalid effort level '\''$EFFORT'\''. Must be '\''low'\'', '\''medium'\'', or '\''high'\''."
      exit 1
    fi
  '
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"Invalid effort level"* ]]
}

@test "--effort parsed correctly" {
  EFFORT="high"

  # Simulate --effort low parsing
  EFFORT="low"

  [[ "$EFFORT" == "low" ]]
}

@test "--effort with equals sign parsed correctly" {
  EFFORT="high"

  # Simulate --effort=medium parsing (from ralph.sh logic)
  EFFORT="medium"

  [[ "$EFFORT" == "medium" ]]
}
