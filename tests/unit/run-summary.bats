#!/usr/bin/env bats

load '../helpers/common'

setup() {
  source "$PROJECT_ROOT/lib/summary.sh"
}

@test "print_summary outputs all required fields" {
  run print_summary 3 125 5 10 "all tasks done" 0 1 10 20 30 40 25
  [ "$status" -eq 0 ]
  [[ "$output" == *"Exit reason:"* ]]
  [[ "$output" == *"Tasks completed:"* ]]
  [[ "$output" == *"Tasks remaining:"* ]]
  [[ "$output" == *"Iterations used:"* ]]
  [[ "$output" == *"Failed iterations:"* ]]
  [[ "$output" == *"Total wall time:"* ]]
}

@test "print_summary shows correct values" {
  run print_summary 3 3661 5 10 "max iterations reached" 2 1 60 120 180 240 300
  [ "$status" -eq 0 ]
  [[ "$output" == *"Tasks completed:    3"* ]]
  [[ "$output" == *"Exit reason:        max iterations reached"* ]]
  [[ "$output" == *"Tasks remaining:    2"* ]]
  [[ "$output" == *"Iterations used:    5 of 10"* ]]
  [[ "$output" == *"Failed iterations:  1"* ]]
  [[ "$output" == *"1h 1m 1s"* ]]
}

@test "print_summary shows exit reason: error" {
  run print_summary 1 60 2 10 "error" 5 1 30 30
  [ "$status" -eq 0 ]
  [[ "$output" == *"Exit reason:        error"* ]]
}

@test "print_summary shows exit reason: interrupted" {
  run print_summary 0 10 1 5 "interrupted" 3 0 10
  [ "$status" -eq 0 ]
  [[ "$output" == *"Exit reason:        interrupted"* ]]
}

@test "print_summary shows per-iteration durations" {
  run print_summary 2 300 2 5 "all tasks done" 0 0 120 180
  [ "$status" -eq 0 ]
  [[ "$output" == *"Per-iteration durations:"* ]]
  [[ "$output" == *"Iteration 1: 2m 0s"* ]]
  [[ "$output" == *"Iteration 2: 3m 0s"* ]]
}

@test "print_summary with zero iterations has no per-iteration section" {
  run print_summary 0 5 0 10 "all tasks done" 0 0
  [ "$status" -eq 0 ]
  [[ "$output" != *"Per-iteration durations:"* ]]
}

@test "print_summary output is plain text not markdown" {
  run print_summary 1 60 1 5 "all tasks done" 0 0 60
  [ "$status" -eq 0 ]
  [[ "$output" != *"#"* ]]
  [[ "$output" != *"**"* ]]
  [[ "$output" != *"\`"* ]]
}

@test "format duration: seconds only" {
  run _summary_format_duration 45
  [[ "$output" == "45s" ]]
}

@test "format duration: minutes and seconds" {
  run _summary_format_duration 125
  [[ "$output" == "2m 5s" ]]
}

@test "format duration: hours minutes seconds" {
  run _summary_format_duration 3661
  [[ "$output" == "1h 1m 1s" ]]
}

@test "print_summary shows failed iteration count" {
  run print_summary 2 300 4 10 "max iterations reached" 3 2 60 60 60 60
  [ "$status" -eq 0 ]
  [[ "$output" == *"Failed iterations:  2"* ]]
}
