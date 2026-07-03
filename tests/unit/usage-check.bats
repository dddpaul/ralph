#!/usr/bin/env bats
# Unit tests for plugins/ralph/skills/ralph-run/scripts/usage-check.sh

load '../helpers/common'

USAGE_CHECK="$PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts/usage-check.sh"

setup() {
  setup_test_dir
  CCUSAGE_LOG="$TEST_DIR/ccusage_invocations.log"
  : > "$CCUSAGE_LOG"
}

teardown() {
  cleanup_test_dir
}

# Install a PATH-overriding ccusage mock that emits the given JSON.
# All ccusage invocations are recorded in $CCUSAGE_LOG.
mock_ccusage_json() {
  local json="$1"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/ccusage" <<EOF
#!/bin/bash
echo "\$@" >> "$CCUSAGE_LOG"
cat <<'JSONEOF'
$json
JSONEOF
EOF
  chmod +x "$TEST_DIR/bin/ccusage"
}

# Install a ccusage mock that exits non-zero.
mock_ccusage_fail() {
  local rc="${1:-1}"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/ccusage" <<EOF
#!/bin/bash
echo "\$@" >> "$CCUSAGE_LOG"
exit $rc
EOF
  chmod +x "$TEST_DIR/bin/ccusage"
}

# Install a ccusage mock that emits literal raw (non-JSON) text.
mock_ccusage_raw() {
  local body="$1"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/ccusage" <<EOF
#!/bin/bash
echo "\$@" >> "$CCUSAGE_LOG"
printf '%s' '$body'
EOF
  chmod +x "$TEST_DIR/bin/ccusage"
}

# Compute an ISO 8601 endTime N minutes from now (UTC).
endtime_in() {
  local minutes="$1"
  date -u -d "+${minutes} minutes" +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null \
    || date -u -v +${minutes}M +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null
}

@test "BUFFER_MIN=0 short-circuits — does not invoke ccusage" {
  mock_ccusage_fail 1
  export PATH="$TEST_DIR/bin:$PATH"

  run bash "$USAGE_CHECK" 0
  [ "$status" -eq 0 ]
  # Mock should NOT have been called
  [ ! -s "$CCUSAGE_LOG" ]
}

# Capture stdout to a file so the assertion can read the helper's actual stdout
# without bash's "setlocale" warning (emitted on stderr by some hosts) leaking
# into the bats `$output` variable.

@test "no active block (isActive=false) exits 0" {
  local json='{"blocks":[{"isActive":false,"isGap":false,"endTime":"2030-01-01T00:00:00.000Z"}]}'
  mock_ccusage_json "$json"
  export PATH="$TEST_DIR/bin:$PATH"

  local out_file="$TEST_DIR/stdout.log"
  local rc=0
  bash "$USAGE_CHECK" 30 >"$out_file" 2>/dev/null || rc=$?
  [ "$rc" -eq 0 ]
  [ ! -s "$out_file" ]
}

@test "gap block (isGap=true) exits 0" {
  local json='{"blocks":[{"isActive":true,"isGap":true,"endTime":"2030-01-01T00:00:00.000Z"}]}'
  mock_ccusage_json "$json"
  export PATH="$TEST_DIR/bin:$PATH"

  local out_file="$TEST_DIR/stdout.log"
  local rc=0
  bash "$USAGE_CHECK" 30 >"$out_file" 2>/dev/null || rc=$?
  [ "$rc" -eq 0 ]
  [ ! -s "$out_file" ]
}

@test "remaining > buffer (active block) exits 0" {
  local end
  end=$(endtime_in 120)
  local json="{\"blocks\":[{\"isActive\":true,\"isGap\":false,\"endTime\":\"$end\"}]}"
  mock_ccusage_json "$json"
  export PATH="$TEST_DIR/bin:$PATH"

  local out_file="$TEST_DIR/stdout.log"
  local rc=0
  bash "$USAGE_CHECK" 30 >"$out_file" 2>/dev/null || rc=$?
  [ "$rc" -eq 0 ]
  [ ! -s "$out_file" ]
}

@test "remaining <= buffer (active block) exits 1 with reason string" {
  local end
  end=$(endtime_in 5)
  local json="{\"blocks\":[{\"isActive\":true,\"isGap\":false,\"endTime\":\"$end\"}]}"
  mock_ccusage_json "$json"
  export PATH="$TEST_DIR/bin:$PATH"

  local out_file="$TEST_DIR/stdout.log"
  local rc=0
  bash "$USAGE_CHECK" 30 >"$out_file" 2>/dev/null || rc=$?
  [ "$rc" -eq 1 ]
  local stdout
  stdout=$(cat "$out_file")
  [[ "$stdout" == block_end_in_*min_below_30min_buffer ]]
}

@test "ccusage missing exits 2" {
  # Empty PATH (no ccusage)
  run env PATH="/usr/bin:/bin" bash "$USAGE_CHECK" 30
  [ "$status" -eq 2 ]
  [[ "$output" == *"ccusage not found"* ]] || [[ "$output" == *"block-end check skipped"* ]]
}

@test "jq missing exits 2" {
  mock_ccusage_json '{"blocks":[]}'
  # Provide ccusage on PATH but exclude jq (use a minimal PATH with only the mock dir
  # plus /usr/bin/bash etc. — but we need to ensure jq is not findable)
  mkdir -p "$TEST_DIR/bin2"
  ln -sf "$TEST_DIR/bin/ccusage" "$TEST_DIR/bin2/ccusage"
  # Symlink only the essentials
  for cmd in bash sh date head grep sed printf cat echo; do
    if command -v "$cmd" >/dev/null 2>&1; then
      ln -sf "$(command -v "$cmd")" "$TEST_DIR/bin2/$cmd"
    fi
  done

  run env PATH="$TEST_DIR/bin2" bash "$USAGE_CHECK" 30
  [ "$status" -eq 2 ]
  [[ "$output" == *"jq not found"* ]] || [[ "$output" == *"block-end check skipped"* ]]
}

@test "ccusage nonzero exit code yields exit 2" {
  mock_ccusage_fail 1
  export PATH="$TEST_DIR/bin:$PATH"

  run bash "$USAGE_CHECK" 30
  [ "$status" -eq 2 ]
  [[ "$output" == *"ccusage exited"* ]]
}

@test "malformed (non-JSON) ccusage output exits 2" {
  mock_ccusage_raw "not json at all"
  export PATH="$TEST_DIR/bin:$PATH"

  run bash "$USAGE_CHECK" 30
  [ "$status" -eq 2 ]
  [[ "$output" == *"unparseable"* ]] || [[ "$output" == *"block-end check skipped"* ]]
}

@test "endTime field missing exits 2" {
  local json='{"blocks":[{"isActive":true,"isGap":false}]}'
  mock_ccusage_json "$json"
  export PATH="$TEST_DIR/bin:$PATH"

  run bash "$USAGE_CHECK" 30
  [ "$status" -eq 2 ]
  [[ "$output" == *"endTime"* ]] || [[ "$output" == *"block-end check skipped"* ]]
}

@test "non-integer BUFFER_MIN exits 2 with error" {
  run bash "$USAGE_CHECK" not-a-number
  [ "$status" -eq 2 ]
  [[ "$output" == *"non-negative integer"* ]]
}

@test "no BUFFER_MIN arg exits 2 with error" {
  run bash "$USAGE_CHECK"
  [ "$status" -eq 2 ]
  [[ "$output" == *"non-negative integer"* ]]
}
