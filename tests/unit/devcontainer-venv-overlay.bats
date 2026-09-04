#!/usr/bin/env bats
# Unit tests for the .venv container-volume overlay in devcontainer.json.
#
# `workspaceMount` bind-mounts the host project folder at /workspace, so a
# container-side `uv sync` writes .venv/pyvenv.cfg with a container-only
# interpreter home onto the host, leaving .venv/bin/python3 a broken symlink
# there. A named volume mounted over /workspace/.venv keeps the two apart.
#
# The overlay is config, not code — nothing else in the suite would notice if
# the mount were dropped, reworded into a bind, or left root-owned. These tests
# pin the three properties that make it work, on the live file AND on the
# ralph-init template that scaffolds it into new projects.
#
# See TASK-235.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
LIVE="$PROJECT_ROOT/.devcontainer/devcontainer.json"
TEMPLATE="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json"

# devcontainer.json is JSONC — jq cannot read it directly. Every comment in the
# file is a whole-line `//`, so dropping those lines yields parseable JSON.
# Printing through jq also proves the file is still valid after any edit.
strip_jsonc() {
  sed -E 's@^[[:space:]]*//.*$@@' "$1"
}

query() {
  strip_jsonc "$1" | jq -r "$2"
}

# The mount string for /workspace/.venv, or empty when there is none.
venv_mount() {
  query "$1" '.mounts[] | select(test("target=/workspace/\\.venv(,|$)"))'
}

@test "devcontainer.json is valid JSONC in both live and template copies" {
  local f
  for f in "$LIVE" "$TEMPLATE"; do
    run strip_jsonc "$f"
    [ "$status" -eq 0 ]
    echo "$output" | jq -e . > /dev/null
  done
}

@test "a mount targets /workspace/.venv in both live and template copies" {
  local f mount
  for f in "$LIVE" "$TEMPLATE"; do
    mount="$(venv_mount "$f")"
    [ -n "$mount" ]
  done
}

@test "the .venv overlay is a volume, not a bind of a host path" {
  local f mount
  for f in "$LIVE" "$TEMPLATE"; do
    mount="$(venv_mount "$f")"
    # type=volume is what keeps the container venv off the host filesystem;
    # a bind here would reintroduce the exact bug this overlay fixes.
    [[ "$mount" == *"type=volume"* ]]
    [[ "$mount" != *"type=bind"* ]]
    [[ "$mount" != *'${localWorkspaceFolder}'* ]]
    [[ "$mount" != *'${localEnv:'* ]]
  done
}

@test "the .venv volume is scoped per devcontainer, like the .claude overlay" {
  local f mount
  for f in "$LIVE" "$TEMPLATE"; do
    mount="$(venv_mount "$f")"
    # Without ${devcontainerId} the volume would be shared by every project
    # on the machine, so one repo's virtualenv would land in another's.
    [[ "$mount" == *'${devcontainerId}'* ]]
  done
}

@test "postCreateCommand chowns /workspace/.venv to the remote user" {
  local f pcc
  for f in "$LIVE" "$TEMPLATE"; do
    pcc="$(query "$f" '.postCreateCommand')"
    # Docker mounts a fresh named volume root-owned; without the chown, uv
    # runs as node and cannot write the environment.
    [[ "$pcc" == *"chown node:node"* ]]
    [[ "$pcc" == *"/workspace/.venv"* ]]
  done
}

@test "the chown runs before anything else in postCreateCommand" {
  local f pcc head
  for f in "$LIVE" "$TEMPLATE"; do
    pcc="$(query "$f" '.postCreateCommand')"
    head="${pcc%%&&*}"
    [[ "$head" == *"/workspace/.venv"* ]]
  done
}

@test "the workspace is still bind-mounted, so the overlay is still needed" {
  local f ws
  for f in "$LIVE" "$TEMPLATE"; do
    ws="$(query "$f" '.workspaceMount')"
    # If this ever stops being a bind of the host folder, the overlay's
    # rationale changes and these tests should be revisited rather than kept
    # passing by accident.
    [[ "$ws" == *"type=bind"* ]]
    [[ "$ws" == *"target=/workspace"* ]]
  done
}

@test "live and template devcontainer.json stay byte-identical" {
  # R11 parity is also asserted in template-parity.bats; repeated here so a
  # failure of these overlay tests points at the right file straight away.
  run diff "$LIVE" "$TEMPLATE"
  [ "$status" -eq 0 ]
}
