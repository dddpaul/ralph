#!/usr/bin/env bats

load '../helpers/common'

setup() {
  setup_test_dir
}

teardown() {
  cleanup_test_dir
}

@test "on-error continue: TASKS_COMPLETED excludes failed iterations" {
  mock_backlog "TASK-1 - Test task"
  mkdir -p "$TEST_DIR/bin"
  local call_count_file="$TEST_DIR/call_count"
  echo "0" > "$call_count_file"
  cat > "$TEST_DIR/bin/opencode" <<MOCK
#!/bin/bash
count=\$(cat "$call_count_file")
count=\$((count + 1))
echo "\$count" > "$call_count_file"
if [ "\$count" -eq 2 ]; then
  exit 1
fi
echo "iteration done"
exit 0
MOCK
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"

  cd "$PROJECT_ROOT"
  run timeout 15 bash ralph.sh --tool opencode --on-error continue 3
  [[ "$output" == *"Tasks completed:    2"* ]]
  [[ "$output" == *"Failed iterations:  1"* ]]
  [[ "$output" == *"Iterations used:    3 of 3"* ]]

  local tasks_done errors
  tasks_done=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d['tasks_done']))" "$RALPH_STATUS_FILE")
  errors=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d['errors']))" "$RALPH_STATUS_FILE")
  [ "$errors" -eq 1 ]
}
