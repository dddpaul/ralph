#!/usr/bin/env bats
# Reproducer tests for tee process-substitution buffering on crash (TASK-21)

load '../helpers/common'

setup() {
  setup_test_dir
}

teardown() {
  cleanup_test_dir
}

create_crash_script() {
  local signal="$1"
  local outfile="$2"
  local line_count="${3:-1000}"
  local script="$TEST_DIR/crash-test.sh"

  cat > "$script" <<SCRIPT
#!/bin/bash
exec > >(tee -a "$outfile") 2>&1
for i in \$(seq 1 $line_count); do
  echo "line \$i"
done
echo "FINAL_LINE"
sleep 0.1
kill -${signal} \$\$
SCRIPT
  chmod +x "$script"
  echo "$script"
}

@test "tee via process substitution preserves output on SIGKILL" {
  local outfile="$TEST_DIR/tee-sigkill.log"
  local script
  script=$(create_crash_script 9 "$outfile" 1000)

  "$script" 2>/dev/null || true
  sleep 0.5

  run grep -c "FINAL_LINE" "$outfile"
  [[ "$output" == "1" ]]
}

@test "tee via process substitution preserves output on SIGTERM" {
  local outfile="$TEST_DIR/tee-sigterm.log"
  local script
  script=$(create_crash_script 15 "$outfile" 1000)

  "$script" 2>/dev/null || true
  sleep 0.5

  run grep -c "FINAL_LINE" "$outfile"
  [[ "$output" == "1" ]]
}

@test "tee via process substitution preserves output on exit 1" {
  local outfile="$TEST_DIR/tee-exit.log"
  local script="$TEST_DIR/exit-test.sh"

  cat > "$script" <<'SCRIPT'
#!/bin/bash
exec > >(tee -a "$1") 2>&1
for i in $(seq 1 100); do
  echo "line $i"
done
echo "FINAL_LINE"
exit 1
SCRIPT
  chmod +x "$script"

  "$script" "$outfile" 2>/dev/null || true
  sleep 0.5

  run grep -c "FINAL_LINE" "$outfile"
  [[ "$output" == "1" ]]
}

@test "tee via process substitution handles large burst before SIGKILL" {
  local outfile="$TEST_DIR/tee-burst.log"
  local script
  script=$(create_crash_script 9 "$outfile" 10000)

  "$script" 2>/dev/null || true
  sleep 1

  run grep -c "FINAL_LINE" "$outfile"
  [[ "$output" == "1" ]]
}
