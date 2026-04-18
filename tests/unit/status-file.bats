#!/usr/bin/env bats

load '../helpers/common'

setup() {
  setup_test_dir
  source "$PROJECT_ROOT/lib/status.sh"
}

teardown() {
  cleanup_test_dir
}

@test "write_status creates valid JSON" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "running" 1 10 "claude" 5 "TASK-3" "" 60 "" "" "" ""
  [ -f "$f" ]
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f"
}

@test "write_status includes all required fields" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "running" 2 10 "claude" 5 "TASK-3" 120 300 "" "" "TASK-1" "some error"
  local content
  content=$(cat "$f")
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

@test "write_status state=running" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "running" 1 10 "claude" 3 "" "" 0 "" "" "" ""
  local state
  state=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['state'])" "$f")
  [[ "$state" == "running" ]]
}

@test "write_status state=completed with completed_at and exit_code" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "completed" 5 10 "claude" 0 "" 180 600 "2026-04-18T12:10:00Z" "0" "TASK-1
TASK-2" ""
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['state'])
print(d['completed_at'])
print(d['exit_code'])
print(len(d['tasks_done']))
" "$f")
  [[ "$(echo "$j" | sed -n '1p')" == "completed" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "2026-04-18T12:10:00Z" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "0" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "2" ]]
}

@test "write_status state=failed with errors" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "failed" 3 10 "opencode" 2 "" 60 180 "2026-04-18T12:03:00Z" "1" "" "Iteration 3 failed with exit code 1"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['state'])
print(d['exit_code'])
print(len(d['errors']))
print(d['errors'][0])
" "$f")
  [[ "$(echo "$j" | sed -n '1p')" == "failed" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "1" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "1" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "Iteration 3 failed with exit code 1" ]]
}

@test "write_status null fields when empty" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "running" 0 10 "claude" 5 "" "" 0 "" "" "" ""
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['current_task'] is None)
print(d['last_iteration_duration'] is None)
print(d['completed_at'] is None)
print(d['exit_code'] is None)
" "$f")
  [[ "$(echo "$j" | sed -n '1p')" == "True" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "True" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "True" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "True" ]]
}

@test "write_status empty arrays for tasks_done and errors" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "running" 1 10 "claude" 3 "" "" 0 "" "" "" ""
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(type(d['tasks_done']).__name__)
print(len(d['tasks_done']))
print(type(d['errors']).__name__)
print(len(d['errors']))
" "$f")
  [[ "$(echo "$j" | sed -n '1p')" == "list" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "0" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "list" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "0" ]]
}

@test "write_status multiple tasks_done as newline-separated" {
  local f="$TEST_DIR/status.json"
  local tasks_done="TASK-1
TASK-2
TASK-3"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "completed" 5 10 "claude" 0 "" 120 600 "2026-04-18T12:10:00Z" "0" "$tasks_done" ""
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(','.join(d['tasks_done']))
" "$f")
  [[ "$j" == "TASK-1,TASK-2,TASK-3" ]]
}

@test "write_status multiple errors as newline-separated" {
  local f="$TEST_DIR/status.json"
  local errors="Iteration 1 failed with exit code 1
Iteration 2 timed out after 15m"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "failed" 3 10 "opencode" 2 "" 60 300 "2026-04-18T12:05:00Z" "1" "" "$errors"
  local j
  j=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(len(d['errors']))
print(d['errors'][0])
print(d['errors'][1])
" "$f")
  [[ "$(echo "$j" | sed -n '1p')" == "2" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "Iteration 1 failed with exit code 1" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "Iteration 2 timed out after 15m" ]]
}

@test "write_status escapes quotes in strings" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "running" 1 10 "claude" 3 'TASK-1 "quoted"' "" 0 "" "" "" 'error "msg"'
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f"
}

@test "write_status numeric fields are numbers not strings" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 9999 "2026-04-18T12:00:00Z" "running" 3 10 "claude" 5 "TASK-1" 120 300 "" "" "" ""
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
" "$f")
  [[ "$(echo "$j" | sed -n '1p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '2p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '3p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '4p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '5p')" == "int" ]]
  [[ "$(echo "$j" | sed -n '6p')" == "int" ]]
}

@test "write_status overwrites existing file" {
  local f="$TEST_DIR/status.json"
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "running" 1 10 "claude" 5 "" "" 0 "" "" "" ""
  write_status "$f" 1234 "2026-04-18T12:00:00Z" "completed" 5 10 "claude" 0 "" 120 600 "2026-04-18T12:10:00Z" "0" "" ""
  local state
  state=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['state'])" "$f")
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
