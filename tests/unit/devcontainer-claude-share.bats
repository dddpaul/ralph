#!/usr/bin/env bats
# Unit tests for the shared-.claude scheme in devcontainer.json.
#
# The template used to mount a named volume over /workspace/.claude and fill it
# once, in postCreateCommand, from a read-only bind of the host's project
# .claude. Because postCreateCommand runs only at container creation, every
# later run worked against a stale copy: host edits never reached the container,
# and container commits carried the stale copy back into git, silently reverting
# .claude/skills/** files after autonomous runs.
#
# The fix shares the directory (it already arrives via workspaceMount) and
# overrides exactly one file — .claude/settings.local.json — because bwrap
# cannot create mount namespaces on Docker Desktop macOS, so the sandbox has to
# be off in the container while the host keeps it on. Two lifecycle hooks go
# with it: an initializeCommand that seeds the host file so Docker cannot leave
# a 0-byte unparsable one in its place, and a postCreateCommand that grants git
# safe.directory on /workspace (which presents as root-owned to the node user,
# so git would otherwise refuse the repo with "detected dubious ownership").
#
# All of this is config, not code: nothing else in the suite would notice if the
# volume came back, the override widened into a permission allowlist, or either
# hook were dropped. These tests pin it on the live file AND on the ralph-init
# template that scaffolds it into new projects.
#
# See TASK-239. The .venv volume overlay is covered by
# devcontainer-venv-overlay.bats.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
LIVE="$PROJECT_ROOT/.devcontainer/devcontainer.json"
TEMPLATE="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json"
LIVE_SETTINGS="$PROJECT_ROOT/.devcontainer/container-settings.local.json"
TEMPLATE_SETTINGS="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/devcontainer/container-settings.local.json"

# devcontainer.json is JSONC — jq cannot read it directly. Every comment in the
# file is a whole-line `//`, so dropping those lines yields parseable JSON.
strip_jsonc() {
  sed -E 's@^[[:space:]]*//.*$@@' "$1"
}

query() {
  strip_jsonc "$1" | jq -r "$2"
}

# The mount string targeting /workspace/.claude/settings.local.json, or empty.
settings_mount() {
  query "$1" '.mounts[] | select(test("target=/workspace/\\.claude/settings\\.local\\.json(,|$)"))'
}

@test "no mount targets the .claude directory itself" {
  local f offenders
  for f in "$LIVE" "$TEMPLATE"; do
    # A whole-directory mount is the defect: it hides host edits from the
    # container and lets container commits revert .claude files.
    offenders="$(query "$f" '.mounts[] | select(test("target=/workspace/\\.claude(,|$)"))')"
    [ -z "$offenders" ] || {
      echo "$f still mounts over the .claude directory: $offenders"
      return 1
    }
  done
}

@test "no read-only bind of the host project .claude remains" {
  local f
  for f in "$LIVE" "$TEMPLATE"; do
    # /workspace-host-claude was the staging bind the copy read from; with the
    # copy gone it has no purpose, and leaving it invites the copy back.
    ! grep -q 'workspace-host-claude' "$f"
    ! grep -q 'claude-code-project-config' "$f"
  done
}

@test "one mount binds the container settings file over .claude/settings.local.json" {
  local f mount
  for f in "$LIVE" "$TEMPLATE"; do
    mount="$(settings_mount "$f")"
    [ -n "$mount" ]
    [[ "$mount" == *"type=bind"* ]]
    [[ "$mount" != *"type=volume"* ]]
    # Sourced from the repo so it is reviewable and travels with a clone.
    [[ "$mount" == *'${localWorkspaceFolder}/.devcontainer/container-settings.local.json'* ]]
  done
}

@test "exactly one mount targets anything under /workspace/.claude" {
  local f count
  for f in "$LIVE" "$TEMPLATE"; do
    count="$(strip_jsonc "$f" \
      | jq '[.mounts[] | select(test("target=/workspace/\\.claude"))] | length')"
    [ "$count" -eq 1 ]
  done
}

@test "the container settings file ships in both live and template trees" {
  local f
  for f in "$LIVE_SETTINGS" "$TEMPLATE_SETTINGS"; do
    [ -f "$f" ]
    run jq -e . "$f"
    [ "$status" -eq 0 ]
  done
  run diff "$LIVE_SETTINGS" "$TEMPLATE_SETTINGS"
  [ "$status" -eq 0 ]
}

@test "the container settings file carries only the sandbox switch" {
  local f
  for f in "$LIVE_SETTINGS" "$TEMPLATE_SETTINGS"; do
    # Ralph runs claude with --dangerously-skip-permissions in the container,
    # so an allowlist here would be dead weight that drifts from the host's.
    run diff <(jq -S '[paths | join(".")]' "$f") \
             <(printf '%s\n' '[' '  "sandbox",' '  "sandbox.enabled"' ']')
    [ "$status" -eq 0 ] || {
      echo "$f is not just the sandbox switch:"
      echo "$output"
      return 1
    }
    [ "$(jq -r '.sandbox.enabled' "$f")" = "false" ]
  done
}

@test "initializeCommand seeds the host settings file when missing or empty" {
  local f cmd
  for f in "$LIVE" "$TEMPLATE"; do
    cmd="$(query "$f" '.initializeCommand')"
    [ "$cmd" != "null" ]
    [[ "$cmd" == *".claude/settings.local.json"* ]]
    # [ -s ] is what makes it idempotent and leaves a real host file alone;
    # [ -f ] would leave a 0-byte file in place, which is the failure mode.
    [[ "$cmd" == *"-s "* ]]
    # The directory must exist before the redirect: on a fresh clone with no
    # .claude, the redirect fails, sh exits non-zero, and the devcontainer CLI
    # aborts container creation.
    [[ "$cmd" == *"mkdir -p .claude"* ]]
  done
}

@test "the seeding command really is idempotent and repairs an empty file" {
  # Run the actual command string from the file in a scratch workspace, the
  # way Docker does: /bin/sh -c with the working directory at the project root.
  local cmd tmp
  cmd="$(query "$TEMPLATE" '.initializeCommand')"
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/.claude"

  # missing -> created and parseable
  ( cd "$tmp" && eval "$cmd" )
  jq -e . "$tmp/.claude/settings.local.json" > /dev/null

  # empty -> repaired
  : > "$tmp/.claude/settings.local.json"
  ( cd "$tmp" && eval "$cmd" )
  jq -e . "$tmp/.claude/settings.local.json" > /dev/null

  # real file -> untouched
  printf '{"sandbox":{"enabled":true}}\n' > "$tmp/.claude/settings.local.json"
  ( cd "$tmp" && eval "$cmd" )
  [ "$(jq -r '.sandbox.enabled' "$tmp/.claude/settings.local.json")" = "true" ]

  rm -rf "$tmp"
}

@test "the seeding command succeeds in a clone with no .claude directory" {
  # A fresh clone may lack .claude entirely (gitignored or never committed).
  # Docker runs initializeCommand as /bin/sh -c from the project root.
  local f cmd tmp
  for f in "$LIVE" "$TEMPLATE"; do
    cmd="$(query "$f" '.initializeCommand')"
    tmp="$(mktemp -d)"
    run sh -c "cd '$tmp' && $cmd"
    [ "$status" -eq 0 ]
    [ "$(cat "$tmp/.claude/settings.local.json")" = "{}" ]
    rm -rf "$tmp"
  done
}

@test "postCreateCommand grants git safe.directory on the workspace" {
  local f pcc
  for f in "$LIVE" "$TEMPLATE"; do
    pcc="$(query "$f" '.postCreateCommand')"
    # Without this the node user gets "detected dubious ownership" and Ralph
    # has no git at all — no status, no commit.
    [[ "$pcc" == *"safe.directory"* ]]
    [[ "$pcc" == *"/workspace"* ]]
    [[ "$pcc" == *"--global"* ]]
  done
}

@test "postCreateCommand no longer copies the .claude directory" {
  local f pcc
  for f in "$LIVE" "$TEMPLATE"; do
    pcc="$(query "$f" '.postCreateCommand')"
    [[ "$pcc" != *"workspace-host-claude"* ]]
    [[ "$pcc" != *"cp -a"* ]]
    # The old command patched sandbox.enabled with jq in place; the bind does
    # that declaratively now.
    [[ "$pcc" != *"sandbox.enabled"* ]]
  done
}

@test "the project .claude still arrives through the workspace bind" {
  local f ws
  for f in "$LIVE" "$TEMPLATE"; do
    ws="$(query "$f" '.workspaceMount')"
    # Sharing the directory only works because the whole project folder is
    # bind-mounted; if that ever changes, this scheme needs revisiting rather
    # than passing by accident.
    [[ "$ws" == *"type=bind"* ]]
    [[ "$ws" == *'source=${localWorkspaceFolder}'* ]]
    [[ "$ws" == *"target=/workspace"* ]]
  done
}
