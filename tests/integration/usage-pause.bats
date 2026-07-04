#!/usr/bin/env bats
# Integration tests for the --block-end-buffer-min usage-pause feature.
# Covers preflight.sh refusal/warn paths, the ralph.sh main-loop pause path,
# and the per-iteration once-only warn invariant.

load '../helpers/common'

PREFLIGHT="$PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts/preflight.sh"

setup() {
  setup_test_dir
  # A real-ish ralph.sh placeholder for preflight tests
  mkdir -p "$TEST_DIR/backlog"
  cat > "$TEST_DIR/ralph.sh" <<'RALPH'
#!/bin/bash
echo "fake ralph"
RALPH
  chmod +x "$TEST_DIR/ralph.sh"
}

teardown() {
  cleanup_test_dir
}

# Compose a PATH-overriding ccusage mock returning JSON with an endTime
# N minutes from now. Active block, isGap=false.
mock_ccusage_active_endtime() {
  local minutes_from_now="$1"
  local end
  end=$(date -u -d "+${minutes_from_now} minutes" +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null \
    || date -u -v +${minutes_from_now}M +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null)
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/ccusage" <<EOF
#!/bin/bash
cat <<JSONEOF
{"blocks":[{"isActive":true,"isGap":false,"endTime":"$end"}]}
JSONEOF
EOF
  chmod +x "$TEST_DIR/bin/ccusage"
}

# Mock ccusage to fail (so usage-check returns 2).
mock_ccusage_broken() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/ccusage" <<'EOF'
#!/bin/bash
exit 1
EOF
  chmod +x "$TEST_DIR/bin/ccusage"
}

@test "preflight refuses launch when usage-check returns 1 (block ending soon)" {
  # Block ends in 5 minutes, buffer is 30 — should trip
  mock_ccusage_active_endtime 5
  mock_backlog "TASK-1 - test"
  mkdir -p "$TEST_DIR/bin"
  # Mock devcontainer just in case
  cat > "$TEST_DIR/bin/devcontainer" <<'EOF'
#!/bin/bash
echo "mock devcontainer"
EOF
  chmod +x "$TEST_DIR/bin/devcontainer"

  cd "$TEST_DIR"
  local rc=0
  out=$(PATH="$TEST_DIR/bin:$PATH" bash "$PREFLIGHT" "$TEST_DIR/ralph.sh" false --block-end-buffer-min 30 2>&1) || rc=$?
  [ "$rc" -ne 0 ]
  [[ "$out" == *"usage cap tripped"* ]] || [[ "$out" == *"block_end_in_"* ]]
}

@test "preflight warns and continues when usage-check returns 2 (cannot measure), creates disabled-flag file" {
  mock_ccusage_broken
  mock_backlog "TASK-1 - test"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/devcontainer" <<'EOF'
#!/bin/bash
echo "mock devcontainer"
EOF
  chmod +x "$TEST_DIR/bin/devcontainer"

  cd "$TEST_DIR"
  local rc=0
  out=$(PATH="$TEST_DIR/bin:$PATH" bash "$PREFLIGHT" "$TEST_DIR/ralph.sh" false --block-end-buffer-min 30 2>&1) || rc=$?
  [ "$rc" -eq 0 ]
  [[ "$out" == *"OK RALPH_PATH"* ]]
  # Disabled flag must exist after warn-continue
  [ -f "$TEST_DIR/backlog/.ralph-usage-check-disabled" ]
}

@test "preflight does NOT invoke ccusage when --block-end-buffer-min is 0 (default)" {
  # ccusage mock would fail if called; default buffer=0 must skip invocation
  mock_ccusage_broken
  mock_backlog "TASK-1 - test"

  cd "$TEST_DIR"
  local rc=0
  out=$(PATH="$TEST_DIR/bin:$PATH" bash "$PREFLIGHT" "$TEST_DIR/ralph.sh" false 2>&1) || rc=$?
  [ "$rc" -eq 0 ]
  [[ "$out" == *"OK RALPH_PATH"* ]]
  # No disabled flag should exist because the check was skipped, not warn-continued
  [ ! -f "$TEST_DIR/backlog/.ralph-usage-check-disabled" ]
}

@test "ralph.sh main loop sets state=paused and breaks when mid-loop usage-check returns 1" {
  # Active block ends in 5 minutes, buffer 30 → trip
  mock_ccusage_active_endtime 5
  mock_backlog_multi "TASK-1 - test" "No tasks found" "TASK-1 - test"
  mock_tool opencode "done"

  # The mid-loop usage check is owned by the Python orchestrator
  # (ralph/usage_check.py, ported in task-151). It resolves ccusage from PATH —
  # driven here by the mock — and consults no external script or env override,
  # so the trip is asserted purely through the ccusage mock above.
  cd "$PROJECT_ROOT"
  run timeout 15 bash ralph.sh --tool opencode --block-end-buffer-min 30 3
  [ "$status" -eq 0 ]
  [ -f "$RALPH_STATUS_FILE" ]
  local state
  state=$(grep -o '"state":"[^"]*"' "$RALPH_STATUS_FILE" | head -1 | sed 's/.*:"//;s/"$//')
  [[ "$state" == "paused" ]]
  local reason
  reason=$(grep -o '"paused_reason":"[^"]*"' "$RALPH_STATUS_FILE" | head -1 | sed 's/.*:"//;s/"$//')
  [[ "$reason" == block_end_in_*min_below_30min_buffer ]]
  local buffer
  buffer=$(grep -o '"paused_buffer_min":[0-9]*' "$RALPH_STATUS_FILE" | head -1 | sed 's/.*://')
  [ "$buffer" -eq 30 ]
}
