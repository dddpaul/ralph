#!/usr/bin/env bash
# Sourceable run summary for ralph.sh

_summary_format_duration() {
  local seconds="$1"
  local hours=$((seconds / 3600))
  local minutes=$(( (seconds % 3600) / 60 ))
  local secs=$((seconds % 60))

  if [[ $hours -gt 0 ]]; then
    printf "%dh %dm %ds" "$hours" "$minutes" "$secs"
  elif [[ $minutes -gt 0 ]]; then
    printf "%dm %ds" "$minutes" "$secs"
  else
    printf "%ds" "$secs"
  fi
}

print_summary() {
  local tasks_completed="$1"
  local wall_time="$2"
  local iterations_used="$3"
  local max_iterations="$4"
  local exit_reason="$5"
  local tasks_remaining="$6"
  local failed_iterations="$7"
  shift 7
  local iter_durations=("$@")

  echo ""
  echo "==============================="
  echo "  Ralph Run Summary"
  echo "==============================="
  echo "Exit reason:        $exit_reason"
  echo "Tasks completed:    $tasks_completed"
  echo "Tasks remaining:    $tasks_remaining"
  echo "Iterations used:    $iterations_used of $max_iterations"
  echo "Failed iterations:  $failed_iterations"
  echo "Total wall time:    $(_summary_format_duration "$wall_time")"

  if [[ ${#iter_durations[@]} -gt 0 ]]; then
    echo ""
    echo "Per-iteration durations:"
    for idx in "${!iter_durations[@]}"; do
      echo "  Iteration $((idx + 1)): $(_summary_format_duration "${iter_durations[$idx]}")"
    done
  fi
  echo "==============================="
}
