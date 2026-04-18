#!/usr/bin/env bash
# Status file writer for ralph.sh

_status_json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

_status_json_array() {
  local items="$1"
  if [[ -z "$items" ]]; then
    printf '[]'
    return
  fi
  local first=true
  printf '['
  while IFS= read -r item; do
    [[ -z "$item" ]] && continue
    if [[ "$first" == true ]]; then
      first=false
    else
      printf ','
    fi
    printf '"%s"' "$(_status_json_escape "$item")"
  done <<< "$items"
  printf ']'
}

write_status() {
  local status_file="$1"
  local pid="$2"
  local started_at="$3"
  local state="$4"
  local iteration="$5"
  local max_iterations="$6"
  local tool="$7"
  local tasks_remaining="$8"
  local current_task="$9"
  local last_iteration_duration="${10}"
  local elapsed="${11}"
  local completed_at="${12}"
  local exit_code="${13}"
  local tasks_done="${14}"
  local errors="${15}"

  local tasks_done_json errors_json
  tasks_done_json=$(_status_json_array "$tasks_done")
  errors_json=$(_status_json_array "$errors")

  local current_task_json="null"
  [[ -n "$current_task" ]] && current_task_json="\"$(_status_json_escape "$current_task")\""

  local last_iter_json="null"
  [[ -n "$last_iteration_duration" ]] && last_iter_json="$last_iteration_duration"

  local completed_at_json="null"
  [[ -n "$completed_at" ]] && completed_at_json="\"$(_status_json_escape "$completed_at")\""

  local exit_code_json="null"
  [[ -n "$exit_code" ]] && exit_code_json="$exit_code"

  cat > "$status_file" <<STATUSEOF
{"pid":$pid,"started_at":"$(_status_json_escape "$started_at")","state":"$(_status_json_escape "$state")","iteration":$iteration,"max_iterations":$max_iterations,"tool":"$(_status_json_escape "$tool")","tasks_done":$tasks_done_json,"tasks_remaining":${tasks_remaining:-0},"current_task":$current_task_json,"last_iteration_duration":$last_iter_json,"elapsed":$elapsed,"errors":$errors_json,"completed_at":$completed_at_json,"exit_code":$exit_code_json}
STATUSEOF
}
