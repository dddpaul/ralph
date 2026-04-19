#!/usr/bin/env bats

load '../helpers/common'

STATUS_FILE="$PROJECT_ROOT/backlog/.ralph-status.json"
RUN_LOG="$PROJECT_ROOT/backlog/.ralph-run.log"

setup() {
  setup_test_dir
  rm -f "$STATUS_FILE" "$RUN_LOG"
}

teardown() {
  cleanup_test_dir
  rm -f "$STATUS_FILE" "$RUN_LOG"
}

@test "status file created on loop start with state=running" {
  mock_backlog "No tasks found"
  mock_tool opencode "done"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  [ -f "$STATUS_FILE" ]
  local state
  state=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['state'])" "$STATUS_FILE")
  [[ "$state" == "completed" ]]
}

@test "status file state=completed on all-tasks-done exit" {
  mock_backlog "No tasks found"
  mock_tool opencode "done"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['state'])
print(d['exit_code'])
print(d['completed_at'] is not None)
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "completed" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "0" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "True" ]]
}

@test "status file state=completed on COMPLETE signal" {
  mock_tool opencode '<promise>COMPLETE</promise>'
  mock_backlog_multi "TASK-1 - Test task" "No tasks found" "TASK-1 - Test task"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  local state
  state=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['state'])" "$STATUS_FILE")
  [[ "$state" == "completed" ]]
}

@test "status file state=failed on max iterations" {
  mock_tool opencode "iteration done"
  mock_backlog_multi "TASK-1 - Test task" "No tasks found" "TASK-1 - Test task"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 2
  [ "$status" -eq 1 ]
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['state'])
print(d['exit_code'])
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "failed" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "1" ]]
}

@test "status file state=failed on error with on-error=stop" {
  mock_backlog_multi "TASK-1 - Test task" "No tasks found" "TASK-1 - Test task"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode --on-error stop 3
  [ "$status" -ne 0 ]
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['state'])
print(len(d['errors']))
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "failed" ]]
  [[ "$(echo "$j" | sed -n '2p')" -ge 1 ]]
}

@test "status file tracks iteration count" {
  mock_tool opencode "iteration done"
  mock_backlog_multi "TASK-1 - Test task" "No tasks found" "TASK-1 - Test task"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 2
  local iteration
  iteration=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['iteration'])" "$STATUS_FILE")
  [[ "$iteration" == "2" ]]
}

@test "status file has correct tool" {
  mock_backlog "No tasks found"
  mock_tool opencode "done"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  local tool
  tool=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['tool'])" "$STATUS_FILE")
  [[ "$tool" == "opencode" ]]
}

@test "status file has correct max_iterations" {
  mock_backlog "No tasks found"
  mock_tool opencode "done"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 7
  local max
  max=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['max_iterations'])" "$STATUS_FILE")
  [[ "$max" == "7" ]]
}

@test "status file has pid" {
  mock_backlog "No tasks found"
  mock_tool opencode "done"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  local pid
  pid=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['pid'])" "$STATUS_FILE")
  [[ "$pid" -gt 0 ]]
}

@test "status file current_task populated from To Do list" {
  mock_tool opencode '<promise>COMPLETE</promise>'
  mock_backlog_multi "TASK-2 - Test task" "TASK-1 - Done task"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]

  local current_task
  current_task=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['current_task'])" "$STATUS_FILE")
  [[ "$current_task" == "TASK-2" ]]
}

@test "run log file created with output" {
  mock_backlog "No tasks found"
  mock_tool opencode "done"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  [ -f "$RUN_LOG" ]
  local log_content
  log_content=$(cat "$RUN_LOG")
  [[ "$log_content" == *"Starting Ralph"* ]]
}

@test "run log contains iteration output" {
  mock_tool opencode '<promise>COMPLETE</promise>'
  mock_backlog_multi "TASK-1 - Test task" "No tasks found" "No tasks found"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  [ -f "$RUN_LOG" ]
  local log_content
  log_content=$(cat "$RUN_LOG")
  [[ "$log_content" == *"Ralph Iteration 1"* ]]
}

@test "run log contains summary" {
  mock_backlog "No tasks found"
  mock_tool opencode "done"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 3
  [ "$status" -eq 0 ]
  local log_content
  log_content=$(cat "$RUN_LOG")
  [[ "$log_content" == *"Ralph Run Summary"* ]]
}

@test "status file tracks tasks_done when tasks transition to Done" {
  mkdir -p "$TEST_DIR/bin"
  local call_count_file="$TEST_DIR/call_count"
  echo "0" > "$call_count_file"
  cat > "$TEST_DIR/bin/backlog" <<MOCK
#!/bin/bash
prev=""
status=""
for arg in "\$@"; do
  if [[ "\$prev" == "-s" ]]; then
    status="\$arg"
  fi
  prev="\$arg"
done
count=\$(cat "$call_count_file")
case "\$status" in
  "Done")
    if [[ \$count -ge 2 ]]; then
      echo "  TASK-1 - First task"
    else
      echo "No tasks found"
    fi
    ;;
  "In Progress")
    echo "  TASK-1 - First task"
    ;;
  *)
    echo "  TASK-1 - First task"
    ;;
esac
MOCK
  chmod +x "$TEST_DIR/bin/backlog"
  export PATH="$TEST_DIR/bin:$PATH"

  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<MOCK
#!/bin/bash
count=\$(cat "$call_count_file")
count=\$((count + 1))
echo "\$count" > "$call_count_file"
if [[ \$count -ge 2 ]]; then
  echo '<promise>COMPLETE</promise>'
else
  echo "iteration done"
fi
MOCK
  chmod +x "$TEST_DIR/bin/opencode"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode 5
  [ "$status" -eq 0 ]
  local tasks_done
  tasks_done=$(python3 -c "import json,sys; print(','.join(json.load(open(sys.argv[1]))['tasks_done']))" "$STATUS_FILE")
  [[ "$tasks_done" == *"TASK-1"* ]]
}

@test "existing log-file flag still works independently" {
  local error_log="$TEST_DIR/errors.log"
  mock_backlog_multi "TASK-1 - Test task" "No tasks found" "No tasks found"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"

  cd "$PROJECT_ROOT"
  run timeout 10 bash ralph.sh --tool opencode --on-error stop --log-file "$error_log" 3
  [ -f "$error_log" ]
  [[ "$(cat "$error_log")" == *"ERROR"* ]]
  [ -f "$RUN_LOG" ]
}
