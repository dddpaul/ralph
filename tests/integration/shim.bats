#!/usr/bin/env bats
# Resolver tests for the ralph.sh thin shim (US-004; simplified in TASK-212;
# registry lookup in TASK-295).
#
# The shim locates ralph_orchestrator.py by precedence — $RALPH_ORCHESTRATOR,
# then the install recorded in <config>/plugins/installed_plugins.json, else a
# clear error — and
# execs it with `uv run`. These tests stub `uv` on PATH so `uv run
# <orchestrator> ...` reports the resolved path instead of launching the loop,
# letting us assert which tier the resolver selected. The dropped in-repo-source
# and legacy ~/.claude/skills tiers have negative tests below.

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

  # Isolate the resolver: unset the tier-1 override common.bash exports, stub uv
  # first on PATH, and point CLAUDE_CONFIG_DIR at an empty dir so the plugin-cache
  # tier only matches what a test explicitly creates (never the real ~/.claude
  # cache). LC_ALL=C silences bash's setlocale warning so it cannot leak into the
  # captured $output.
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

@test "the two ralph.sh shim copies are byte-identical" {
  diff "$SHIM" "$TEMPLATE_SHIM"
}

@test "resolver tier 1: RALPH_ORCHESTRATOR override wins over the cache" {
  local proj="$TEST_DIR/proj"
  local shim
  shim="$(install_shim "$proj")"

  # Explicit override target.
  local override="$TEST_DIR/override/ralph_orchestrator.py"
  mkdir -p "$(dirname "$override")"
  touch "$override"

  # A plugin-cache install also exists; the explicit override must still win.
  local cfg="$TEST_DIR/cfg"
  local cached="$cfg/plugins/cache/dddpaul-ralph/ralph/v1.0.0/skills/ralph-run/scripts/ralph_orchestrator.py"
  mkdir -p "$(dirname "$cached")"
  touch "$cached"

  run env RALPH_ORCHESTRATOR="$override" CLAUDE_CONFIG_DIR="$cfg" bash "$shim" --help
  [ "$status" -eq 0 ]
  [ "$output" = "UV_RAN=$override" ]
}

# Write a version-2 registry under $1 whose ralph@dddpaul-ralph user-scope
# entry points at $2.
write_registry() {
  mkdir -p "$1/plugins"
  printf '{"version":2,"plugins":{"ralph@dddpaul-ralph":[{"scope":"user","installPath":"%s","version":"0.14.15"}]}}\n' \
    "$2" > "$1/plugins/installed_plugins.json"
}

@test "resolver tier 2: the registered install wins over a newer-sorting fork in the cache" {
  local proj="$TEST_DIR/proj"
  local shim
  shim="$(install_shim "$proj")"
  git -C "$proj" init -q

  local cfg="$TEST_DIR/cfg"
  local cache="$cfg/plugins/cache"
  # sort -V over whole cache paths would pick zz-fork; the registry names
  # dddpaul-ralph 0.14.15, so that is the one the shim must exec.
  local registered="$cache/dddpaul-ralph/ralph/0.14.15/skills/ralph-run/scripts/ralph_orchestrator.py"
  local fork="$cache/zz-fork/ralph/0.1.0/skills/ralph-run/scripts/ralph_orchestrator.py"
  mkdir -p "$(dirname "$registered")" "$(dirname "$fork")"
  touch "$registered" "$fork"
  write_registry "$cfg" "$cache/dddpaul-ralph/ralph/0.14.15"

  run env CLAUDE_CONFIG_DIR="$cfg" bash "$shim" --help
  [ "$status" -eq 0 ]
  [ "$output" = "UV_RAN=$registered" ]
}

@test "refine.sh tier 4: resolves refine_orchestrator.py through the registry" {
  local proj="$TEST_DIR/proj"
  mkdir -p "$proj"
  cp "$REPO_ROOT/refine.sh" "$proj/refine.sh"
  git -C "$proj" init -q

  local cfg="$TEST_DIR/cfg"
  local install="$cfg/plugins/cache/dddpaul-ralph/ralph/0.14.15"
  local orch="$install/skills/ralph-run/scripts/refine_orchestrator.py"
  mkdir -p "$(dirname "$orch")"
  touch "$orch"
  write_registry "$cfg" "$install"

  run env -u REFINE_ORCHESTRATOR CLAUDE_CONFIG_DIR="$cfg" bash "$proj/refine.sh" --help
  [ "$status" -eq 0 ]
  [ "$output" = "UV_RAN=$orch" ]
}

@test "resolver tier 3: clear error and non-zero exit when the plugin is missing" {
  local proj="$TEST_DIR/proj"
  local shim
  shim="$(install_shim "$proj")"

  # Nothing installed: no override and an empty config dir means there is no
  # registry, so the shim exits with the install-the-plugin error.
  git -C "$proj" init -q
  run bash "$shim" --help
  [ "$status" -eq 1 ]
  [[ "$output" == *"plugin registry"*"not found"* ]]
  [[ "$output" == *"could not locate ralph_orchestrator.py"* ]]
  [[ "$output" == *"/plugin install ralph@dddpaul-ralph"* ]]
}

@test "dropped tier: in-repo plugin source is no longer resolved" {
  # Pre-TASK-212 this in-repo path was tier 2 and would have been exec'd. With
  # the tier removed it must be ignored, so the shim falls through to the error.
  local proj="$TEST_DIR/proj"
  local shim
  shim="$(install_shim "$proj")"
  local orch="$proj/plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py"
  mkdir -p "$(dirname "$orch")"
  touch "$orch"

  run bash "$shim" --help
  [ "$status" -eq 1 ]
  [[ "$output" == *"could not locate ralph_orchestrator.py"* ]]
}

@test "dropped tier: legacy ~/.claude/skills install is no longer resolved" {
  # Pre-TASK-212 this legacy path was tier 3 and would have been exec'd. With
  # the tier removed it must be ignored, so the shim falls through to the error.
  local proj="$TEST_DIR/proj"
  local shim
  shim="$(install_shim "$proj")"

  local cfg="$TEST_DIR/legacy-cfg"
  local legacy="$cfg/skills/ralph-run/scripts/ralph_orchestrator.py"
  mkdir -p "$(dirname "$legacy")"
  touch "$legacy"

  run env CLAUDE_CONFIG_DIR="$cfg" bash "$shim" --help
  [ "$status" -eq 1 ]
  [[ "$output" == *"could not locate ralph_orchestrator.py"* ]]
}
