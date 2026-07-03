#!/usr/bin/env bats
# Smoke test for the ralph.sh thin shim.
# Asserts the shim and the canonical produce identical stdout/stderr/exit code
# for a trivial invocation (--help).

load '../helpers/common'

SHIM="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)/ralph.sh"
CANONICAL="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)/plugins/ralph/skills/ralph-run/scripts/ralph.sh"

setup() {
  setup_test_dir
  SHIM_STDOUT="$TEST_DIR/shim.out"
  SHIM_STDERR="$TEST_DIR/shim.err"
  CANON_STDOUT="$TEST_DIR/canon.out"
  CANON_STDERR="$TEST_DIR/canon.err"
}

teardown() {
  cleanup_test_dir
}

@test "shim --help matches canonical --help in stdout, stderr, exit code" {
  # Point the shim at this repo's canonical via CLAUDE_CONFIG_DIR so the test
  # is independent of the user's ~/.claude/skills install state.
  local repo_root
  repo_root=$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)

  # LC_ALL=C silences bash's "setlocale: cannot change locale" warning, which
  # otherwise fires once per bash startup — the shim spawns two bash processes
  # (initial + post-exec replacement) and the canonical only one, so the
  # warning count differs and would defeat a byte-for-byte stderr diff.
  LC_ALL=C CLAUDE_CONFIG_DIR="$repo_root" bash "$SHIM" --help >"$SHIM_STDOUT" 2>"$SHIM_STDERR"
  local shim_rc=$?

  LC_ALL=C bash "$CANONICAL" --help >"$CANON_STDOUT" 2>"$CANON_STDERR"
  local canon_rc=$?

  [ "$shim_rc" -eq "$canon_rc" ]
  [ "$shim_rc" -eq 0 ]
  diff "$SHIM_STDOUT" "$CANON_STDOUT"
  diff "$SHIM_STDERR" "$CANON_STDERR"
}
