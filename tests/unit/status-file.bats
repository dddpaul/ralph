#!/usr/bin/env bats

load '../helpers/common'

setup() {
  setup_test_dir
  RALPH_SOURCE_ONLY=1 source "$PROJECT_ROOT/ralph.sh"
  count_remaining_tasks() { echo "${_TEST_REMAINING:-0}"; }
  STATUS_FILE="$TEST_DIR/status.json"
  RUN_START_TIME=$(date +%s)
  RUN_STARTED_AT="2026-04-18T12:00:00Z"
  CURRENT_ITERATION=1
  MAX_ITERATIONS=10
  TOOL="claude"
  _TEST_REMAINING=0
  CURRENT_TASK=""
  LAST_ITER_DURATION=""
  TASKS_DONE_IDS=""
  STATUS_ERRORS=""
}

teardown() {
  cleanup_test_dir
}

@test "_update_status creates valid JSON" {
  _TEST_REMAINING=5
  CURRENT_TASK="TASK-3"
  _update_status "running"
  [ -f "$STATUS_FILE" ]
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$STATUS_FILE"
}

@test "_update_status includes all required fields" {
  CURRENT_ITERATION=2
  _TEST_REMAINING=5
  CURRENT_TASK="TASK-3"
  LAST_ITER_DURATION=120
  TASKS_DONE_IDS="TASK-1"
  STATUS_ERRORS="some error"
  _update_status "running"
  local content
  content=$(cat "$STATUS_FILE")
  [[ "$content" == *'"pid":'* ]]
  [[ "$content" == *'"started_at":'* ]]
  [[ "$content" == *'"state":'* ]]
  [[ "$content" == *'"iteration":'* ]]
  [[ "$content" == *'"max_iterations":'* ]]
  [[ "$content" == *'"tool":'* ]]
  [[ "$content" == *'"tasks_done":'* ]]
  [[ "$content" == *'"tasks_remaining":'* ]]
  [[ "$content" == *'"current_task":'* ]]
  [[ "$content" == *'"last_iteration_duration":'* ]]
  [[ "$content" == *'"elapsed":'* ]]
  [[ "$content" == *'"errors":'* ]]
  [[ "$content" == *'"completed_at":'* ]]
  [[ "$content" == *'"exit_code":'* ]]
}

@test "_update_status state=running" {
  _TEST_REMAINING=3
  _update_status "running"
  local state
  state=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['state'])" "$STATUS_FILE")
  [[ "$state" == "running" ]]
}

@test "_update_status state=completed with completed_at and exit_code" {
  CURRENT_ITERATION=5
  LAST_ITER_DURATION=180
  TASKS_DONE_IDS="TASK-1
TASK-2"
  _update_status "completed" "2026-04-18T12:10:00Z" "0"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['state'])
print(d['completed_at'])
print(d['exit_code'])
print(len(d['tasks_done']))
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "completed" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "2026-04-18T12:10:00Z" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "0" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "2" ]]
}

@test "_update_status state=failed with errors" {
  CURRENT_ITERATION=3
  TOOL="opencode"
  _TEST_REMAINING=2
  LAST_ITER_DURATION=60
  STATUS_ERRORS="Iteration 3 failed with exit code 1"
  _update_status "failed" "2026-04-18T12:03:00Z" "1"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['state'])
print(d['exit_code'])
print(len(d['errors']))
print(d['errors'][0])
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "failed" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "1" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "1" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "Iteration 3 failed with exit code 1" ]]
}

@test "_update_status null fields when empty" {
  CURRENT_ITERATION=0
  _TEST_REMAINING=5
  _update_status "running"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['current_task'] is None)
print(d['last_iteration_duration'] is None)
print(d['completed_at'] is None)
print(d['exit_code'] is None)
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "True" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "True" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "True" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "True" ]]
}

@test "_update_status empty arrays for tasks_done and errors" {
  _TEST_REMAINING=3
  _update_status "running"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(type(d['tasks_done']).__name__)
print(len(d['tasks_done']))
print(type(d['errors']).__name__)
print(len(d['errors']))
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "list" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "0" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "list" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "0" ]]
}

@test "_update_status multiple tasks_done as newline-separated" {
  CURRENT_ITERATION=5
  LAST_ITER_DURATION=120
  TASKS_DONE_IDS="TASK-1
TASK-2
TASK-3"
  _update_status "completed" "2026-04-18T12:10:00Z" "0"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(','.join(d['tasks_done']))
" "$STATUS_FILE")
  [[ "$j" == "TASK-1,TASK-2,TASK-3" ]]
}

@test "_update_status multiple errors as newline-separated" {
  CURRENT_ITERATION=3
  TOOL="opencode"
  _TEST_REMAINING=2
  LAST_ITER_DURATION=60
  STATUS_ERRORS="Iteration 1 failed with exit code 1
Iteration 2 timed out after 15m"
  _update_status "failed" "2026-04-18T12:05:00Z" "1"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(len(d['errors']))
print(d['errors'][0])
print(d['errors'][1])
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "2" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "Iteration 1 failed with exit code 1" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "Iteration 2 timed out after 15m" ]]
}

@test "_update_status escapes quotes in strings" {
  _TEST_REMAINING=3
  CURRENT_TASK='TASK-1 "quoted"'
  STATUS_ERRORS='error "msg"'
  _update_status "running"
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$STATUS_FILE"
}

@test "_update_status numeric fields are numbers not strings" {
  CURRENT_ITERATION=3
  _TEST_REMAINING=5
  CURRENT_TASK="TASK-1"
  LAST_ITER_DURATION=120
  _update_status "running"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(type(d['pid']).__name__)
print(type(d['iteration']).__name__)
print(type(d['max_iterations']).__name__)
print(type(d['tasks_remaining']).__name__)
print(type(d['elapsed']).__name__)
print(type(d['last_iteration_duration']).__name__)
" "$STATUS_FILE")
  [[ "$(echo "$j" | sed -n '1p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '5p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '6p')" == "int" ]]
}

@test "_update_status overwrites existing file" {
  _TEST_REMAINING=5
  _update_status "running"
  CURRENT_ITERATION=5
  _TEST_REMAINING=0
  LAST_ITER_DURATION=120
  _update_status "completed" "2026-04-18T12:10:00Z" "0"
  local state
  state=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['state'])" "$STATUS_FILE")
  [[ "$state" == "completed" ]]
}

@test "_status_json_escape handles backslashes" {
  run _status_json_escape 'path\to\file'
  [[ "$output" == 'path\\to\\file' ]]
}

@test "_status_json_escape handles newlines" {
  run _status_json_escape $'line1\nline2'
  [[ "$output" == 'line1\nline2' ]]
}

@test "_status_json_array empty input" {
  run _status_json_array ""
  [[ "$output" == "[]" ]]
}

@test "_status_json_array single item" {
  run _status_json_array "TASK-1"
  [[ "$output" == '["TASK-1"]' ]]
}

@test "_status_json_array multiple items" {
  run _status_json_array "TASK-1
TASK-2"
  [[ "$output" == '["TASK-1","TASK-2"]' ]]
}
