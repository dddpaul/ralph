#!/usr/bin/env bats
# Resolver tests for the ralph.sh thin shim (TASK-190 / US-004).
#
# The shim locates ralph_orchestrator.py via a 5-tier precedence and execs it
# with `uv run`. These tests stub `uv` on PATH so `uv run <orchestrator> ...`
# reports the resolved path instead of launching the loop, letting us assert
# which tier the resolver selected.

load '../helpers/common'

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
SHIM="$REPO_ROOT/ralph.sh"
TEMPLATE_SHIM="$REPO_ROOT/plugins/ralph/skills/ralph-init/templates/root/ralph.sh"

setup() {
  setup_test_dir
  # Stub `uv` so `uv run <orchestrator> ...` just reports the resolved path.
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/uv" <<'EOF'
#!/usr/bin/env bash
shift            # drop the "run" subcommand
echo "UV_RAN=$1"
EOF
  chmod +x "$TEST_DIR/bin/uv"

  # Isolate the resolver: no override, stub uv first on PATH, empty config dir
  # (overrides common.bash's in-repo CLAUDE_CONFIG_DIR so legacy/cache tiers
  # only match what a test explicitly creates). LC_ALL=C silences bash's
  # setlocale warning so it cannot leak into the captured $output.
  unset RALPH_ORCHESTRATOR
  export PATH="$TEST_DIR/bin:$PATH"
  export CLAUDE_CONFIG_DIR="$TEST_DIR/empty-config"
  export LC_ALL=C
}

teardown() {
  cleanup_test_dir
}

# Copy the shim into a fresh fake project root and echo the shim path.
install_shim() {
  local proj="$1"
  mkdir -p "$proj"
  cp "$SHIM" "$proj/ralph.sh"
  printf '%s\n' "$proj/ralph.sh"
}

@test "the two ralph.sh shim copies are byte-identical (AC#2)" {
  diff "$SHIM" "$TEMPLATE_SHIM"
}

@test "resolver tier 2: in-repo plugin source is selected" {
  local proj="$TEST_DIR/proj"
  local shim
  shim="$(install_shim "$proj")"
  local orch="$proj/plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py"
  mkdir -p "$(dirname "$orch")"
  touch "$orch"

  run bash "$shim" --help
  [ "$status" -eq 0 ]
  [ "$output" = "UV_RAN=$orch" ]
}

@test "resolver tier 4: newest marketplace plugin-cache install via sort -V" {
  # Fake project has no in-repo source, so resolution falls to the cache tier.
  local proj="$TEST_DIR/proj"
  local shim
  shim="$(install_shim "$proj")"

  local cfg="$TEST_DIR/cfg"
  local cache="$cfg/plugins/cache/dddpaul-ralph/ralph"
  # v0.9.0 vs v0.10.0: a plain lexical sort would pick v0.9.0; sort -V (version
  # sort) correctly picks v0.10.0, so this asserts the resolver uses sort -V.
  local older="$cache/v0.9.0/skills/ralph-run/scripts/ralph_orchestrator.py"
  local newer="$cache/v0.10.0/skills/ralph-run/scripts/ralph_orchestrator.py"
  mkdir -p "$(dirname "$older")" "$(dirname "$newer")"
  touch "$older" "$newer"

  run env CLAUDE_CONFIG_DIR="$cfg" bash "$shim" --help
  [ "$status" -eq 0 ]
  [ "$output" = "UV_RAN=$newer" ]
  [[ "$output" != *"$older"* ]]
}

@test "resolver tier 5: clear error and non-zero exit when the plugin is missing" {
  local proj="$TEST_DIR/proj"
  local shim
  shim="$(install_shim "$proj")"

  # Nothing installed: no override, no in-repo source, empty config dir means
  # neither the legacy skills path nor the plugin cache glob can match.
  run bash "$shim" --help
  [ "$status" -eq 1 ]
  [[ "$output" == *"could not locate ralph_orchestrator.py"* ]]
  [[ "$output" == *"/plugin install ralph@dddpaul-ralph"* ]]
}
