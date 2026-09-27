#!/usr/bin/env bats
# Unit tests for the second bind of the host ~/.claude at its own host path.
#
# Claude Code resolves a plugin through an absolute path recorded in a registry:
# plugins/known_marketplaces.json stores installLocation and installed_plugins.
# json stores installPath, both as *host* paths (e.g. /Users/<user>/.claude/
# plugins/marketplaces/<name>). The template already binds the host ~/.claude at
# /home/node/.claude, which is the same directory under a different name — and a
# different name is exactly what the registry cannot follow. Every user plugin
# then dies with "Marketplace <name> failed to load: cache-miss", the
# task-reviewer agent shipped by ralph@dddpaul-ralph never registers, and the
# Review step of the Task Lifecycle degrades to a plain agent reading a rules
# file while still reporting APPROVED. Binding the same directory a second time
# at target=${localEnv:HOME}/.claude makes the recorded path resolve.
#
# Nothing else in the suite would notice if the mount were dropped as an
# apparent duplicate of the /home/node/.claude bind, reworded into a volume, or
# retargeted — the failure is silent by construction. These tests pin it on the
# live file AND on the ralph-init template that scaffolds it into new projects,
# and the last test mutation-checks them by deriving the pre-fix copy of each
# file and asserting the detector goes quiet.
#
# See TASK-240. The shared project .claude is covered by
# devcontainer-claude-share.bats; the .venv overlay by
# devcontainer-venv-overlay.bats.

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

# The mount string targeting the literal host ~/.claude path, or empty when
# there is none. This is the detector the mutation test drives to empty.
hostpath_mount() {
  query "$1" '.mounts[] | select(test("target=\\$\\{localEnv:HOME\\}/\\.claude(,|$)"))'
}

@test "devcontainer.json is valid JSONC in both live and template copies" {
  local f
  for f in "$LIVE" "$TEMPLATE"; do
    run strip_jsonc "$f"
    [ "$status" -eq 0 ]
    echo "$output" | jq -e . > /dev/null
  done
}

@test "a mount targets the host \${localEnv:HOME}/.claude path in both copies" {
  local f mount
  for f in "$LIVE" "$TEMPLATE"; do
    mount="$(hostpath_mount "$f")"
    [ -n "$mount" ] || {
      echo "$f has no bind at the literal host ~/.claude path;"
      echo "every user plugin will fail to load with cache-miss"
      return 1
    }
  done
}

@test "the host-path mount binds the host .claude to itself" {
  local f mount
  for f in "$LIVE" "$TEMPLATE"; do
    mount="$(hostpath_mount "$f")"
    # Source and target must be the same host path: the whole point is that the
    # absolute path the registry recorded resolves to the same bytes inside.
    [[ "$mount" == *'source=${localEnv:HOME}/.claude'* ]]
    [[ "$mount" == *'target=${localEnv:HOME}/.claude'* ]]
    [[ "$mount" == *"type=bind"* ]]
    # A volume would mount an empty directory over the path — the registry
    # would resolve it and then find no marketplace there.
    [[ "$mount" != *"type=volume"* ]]
  done
}

@test "the /home/node/.claude bind is still there alongside it" {
  local f mount
  for f in "$LIVE" "$TEMPLATE"; do
    # $HOME inside the container is /home/node, so this bind is what makes a
    # bare ~/.claude (used by any tool that ignores CLAUDE_CONFIG_DIR) land on
    # the same shared directory as the config root.
    mount="$(query "$f" '.mounts[] | select(test("target=/home/node/\\.claude(,|$)"))')"
    [ -n "$mount" ]
    [[ "$mount" == *'source=${localEnv:HOME}/.claude'* ]]
    [[ "$mount" == *"type=bind"* ]]
  done
}

@test "CLAUDE_CONFIG_DIR points at the host path this mount provides" {
  local f
  for f in "$LIVE" "$TEMPLATE"; do
    # TASK-241 repointed the config root here. The mount above is what makes
    # that path exist inside the container, so the two must not drift apart:
    # drop the mount and Claude Code starts against a config root that is an
    # empty auto-created directory. The write-direction argument is in
    # devcontainer-claude-config-root.bats.
    [ "$(query "$f" '.containerEnv.CLAUDE_CONFIG_DIR')" = '${localEnv:HOME}/.claude' ]
  done
}

@test "exactly two mounts bind the host .claude directory" {
  local f count
  for f in "$LIVE" "$TEMPLATE"; do
    count="$(strip_jsonc "$f" \
      | jq '[.mounts[] | select(test("source=\\$\\{localEnv:HOME\\}/\\.claude(,|$)"))] | length')"
    # One for CLAUDE_CONFIG_DIR, one for registry path resolution. A third
    # would mean someone added an alias instead of fixing the registry.
    [ "$count" -eq 2 ]
  done
}

@test "the host-path mount carries a comment naming the cache-miss failure" {
  local f comments
  for f in "$LIVE" "$TEMPLATE"; do
    # Without the rationale in the file, the next reader sees two binds of the
    # same source and prunes one as a copy-paste slip.
    comments="$(grep -E '^[[:space:]]*//' "$f")"
    grep -qi 'cache-miss' <<< "$comments" || {
      echo "$f has no comment naming cache-miss"
      return 1
    }
    grep -qi 'not a duplicate' <<< "$comments" || {
      echo "$f has no comment warning the mount is not a duplicate"
      return 1
    }
  done
}

@test "live and template devcontainer.json stay byte-identical" {
  # R11 parity is also asserted in template-parity.bats; repeated here so a
  # failure of these tests points at the right file straight away.
  run diff "$LIVE" "$TEMPLATE"
  [ "$status" -eq 0 ]
}

@test "the mount assertion fails against the pre-fix copy of each file" {
  # Mutation check: without it, a detector with a typo'd regex would pass on
  # both files forever and the suite would prove nothing. Derive the pre-fix
  # version by deleting the mount line and its comment block from a scratch
  # copy, then assert the detector goes quiet on it — an over-broad regex such
  # as target=.*\.claude would still match there and is caught only here.
  local f pre tmp
  tmp="$(mktemp -d)"
  for f in "$LIVE" "$TEMPLATE"; do
    pre="$tmp/pre-fix-$(basename "$(dirname "$f")").json"
    # Drop the target=${localEnv:HOME}/.claude mount and the comment lines
    # introduced with it; the /home/node/.claude bind is left untouched.
    grep -v 'target=${localEnv:HOME}/.claude' "$f" \
      | grep -v 'cache-miss' \
      | grep -v 'NOT a duplicate' > "$pre"

    # The pre-fix file is still valid JSONC — so a green suite could not have
    # been explained away as "the old file was broken anyway".
    strip_jsonc "$pre" | jq -e . > /dev/null

    # The detector finds nothing: this is the defect state.
    [ -z "$(hostpath_mount "$pre")" ] || {
      echo "mutation check is vacuous: the detector still matches after the"
      echo "host-path mount was removed from $f"
      return 1
    }

    # And the /home/node/.claude bind survived the mutation, proving the two
    # binds are distinguishable and only the new one was removed.
    [ -n "$(query "$pre" '.mounts[] | select(test("target=/home/node/\\.claude(,|$)"))')" ]

    # The real file is not in that state.
    [ -n "$(hostpath_mount "$f")" ]
  done
  rm -rf "$tmp"
}
