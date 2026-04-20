#!/usr/bin/env bats

load '../helpers/common'

setup() {
  setup_test_dir
  mock_backlog "No tasks found"
  RALPH_SOURCE_ONLY=1 source "$RALPH_SCRIPT"
}

teardown() {
  cleanup_test_dir
}

reset_defaults() {
  TOOL="claude"
  MODEL="claude-opus-4-6"
  EFFORT="medium"
  TIMEOUT=15
  MAX_ITERATIONS=10
  USE_DEVCONTAINER=false
  ON_ERROR="stop"
  RETRY_COUNT=2
  LOG_FILE=""
  PROMPT_FILE=""
}

@test "AC1: --tool opencode accepted as valid" {
  reset_defaults
  parse_args --tool opencode
  validate_args
  [[ "$TOOL" == "opencode" ]]
}

@test "AC2: Invalid tool rejected with exit code 1" {
  reset_defaults
  parse_args --tool invalid-tool
  run validate_args
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"Invalid tool"* ]]
}

@test "AC3: --timeout parsed correctly" {
  reset_defaults
  parse_args --timeout 30
  [[ "$TIMEOUT" == "30" ]]
}

@test "AC3: --timeout with equals sign parsed correctly" {
  reset_defaults
  parse_args --timeout=45
  [[ "$TIMEOUT" == "45" ]]
}

@test "AC4: max_iterations parsed from positional argument" {
  reset_defaults
  parse_args 5
  [[ "$MAX_ITERATIONS" == "5" ]]
}

@test "AC4: Non-numeric positional argument rejected" {
  reset_defaults
  run parse_args invalid
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"Unexpected argument"* ]]
}

@test "AC5: Help text shows opencode in usage" {
  grep -q "opencode" "$RALPH_SCRIPT"
  run grep "Usage.*opencode" "$RALPH_SCRIPT"
  [[ "$status" -eq 0 ]]
}

@test "Tool validation: claude is valid" {
  reset_defaults
  parse_args --tool claude
  validate_args
  [[ "$TOOL" == "claude" ]]
}

@test "Tool validation: empty tool is invalid" {
  reset_defaults
  parse_args --tool ""
  run validate_args
  [[ "$status" -eq 1 ]]
}

@test "Default values are correct" {
  reset_defaults
  [[ "$TOOL" == "claude" ]]
  [[ "$MODEL" == "claude-opus-4-6" ]]
  [[ "$EFFORT" == "medium" ]]
  [[ "$TIMEOUT" == "15" ]]
  [[ "$MAX_ITERATIONS" == "10" ]]
  [[ "$USE_DEVCONTAINER" == "false" ]]
}

@test "Effort validation: low is valid" {
  reset_defaults
  parse_args --effort low
  validate_args
  [[ "$EFFORT" == "low" ]]
}

@test "Effort validation: medium is valid" {
  reset_defaults
  parse_args --effort medium
  validate_args
  [[ "$EFFORT" == "medium" ]]
}

@test "Effort validation: high is valid" {
  reset_defaults
  parse_args --effort high
  validate_args
  [[ "$EFFORT" == "high" ]]
}

@test "Effort validation: max is valid" {
  reset_defaults
  parse_args --effort max
  validate_args
  [[ "$EFFORT" == "max" ]]
}

@test "Effort validation: invalid value rejected" {
  reset_defaults
  parse_args --effort extreme
  run validate_args
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"Invalid effort level"* ]]
}

@test "--effort with equals sign parsed correctly" {
  reset_defaults
  parse_args --effort=medium
  validate_args
  [[ "$EFFORT" == "medium" ]]
}

@test "--effort=max with equals sign parsed correctly" {
  reset_defaults
  parse_args --effort=max
  validate_args
  [[ "$EFFORT" == "max" ]]
}

@test "--prompt-file parsed correctly" {
  echo "test prompt" > "$TEST_DIR/prompt.txt"
  reset_defaults
  parse_args --prompt-file "$TEST_DIR/prompt.txt"
  validate_args
  [[ "$PROMPT_FILE" == "$TEST_DIR/prompt.txt" ]]
}

@test "--prompt-file with equals sign parsed correctly" {
  echo "test prompt" > "$TEST_DIR/prompt.txt"
  reset_defaults
  parse_args "--prompt-file=$TEST_DIR/prompt.txt"
  validate_args
  [[ "$PROMPT_FILE" == "$TEST_DIR/prompt.txt" ]]
}

@test "--prompt-file validation: non-existent file rejected with exit code 1" {
  reset_defaults
  parse_args --prompt-file "/tmp/nonexistent-ralph-prompt-file-$$"
  run validate_args
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"does not exist or is not readable"* ]]
}

@test "--prompt-file validation: empty value skips validation" {
  reset_defaults
  validate_args
  [[ "$PROMPT_FILE" == "" ]]
}

@test "--prompt-file validation: readable file accepted" {
  echo "test prompt" > "$TEST_DIR/prompt.txt"
  reset_defaults
  parse_args --prompt-file "$TEST_DIR/prompt.txt"
  validate_args
  [[ "$PROMPT_FILE" == "$TEST_DIR/prompt.txt" ]]
}
