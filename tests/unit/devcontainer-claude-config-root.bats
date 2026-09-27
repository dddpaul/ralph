#!/usr/bin/env bats
# Unit tests for the container's Claude config root (TASK-241).
#
# The devcontainer shares ONE Claude config directory between two machines with
# different filesystem roots. Claude Code's plugin registries store *absolute*
# paths — plugins/known_marketplaces.json stores installLocation and
# plugins/installed_plugins.json stores installPath — and it writes whichever
# root CLAUDE_CONFIG_DIR names. Rooted at /home/node/.claude a container run
# bakes container-only paths into the shared registries; back on the host every
# such entry is rejected outright ("Marketplace <name> has a corrupted
# installLocation (/home/node/...) — expected a path inside
# <config>/plugins/marketplaces"), so the whole plugin ecosystem stops
# resolving, not just ralph@dddpaul-ralph. TASK-240's second bind fixes the
# read direction only; this is the write direction.
#
# The fix: point CLAUDE_CONFIG_DIR at ${localEnv:HOME}/.claude — the same
# directory under its host name, which the second bind already makes present in
# the container. Both machines then record and resolve one path shape.
#
# The mount that makes that path exist is pinned by
# devcontainer-claude-hostpath-bind.bats; here we pin the config root itself
# plus the registry-shape invariant it exists to protect.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
LIVE="$PROJECT_ROOT/.devcontainer/devcontainer.json"
TEMPLATE="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json"

# devcontainer.json is JSONC — drop whole-line // comments to get valid JSON.
strip_jsonc() {
  sed -E 's@^[[:space:]]*//.*$@@' "$1"
}

query() {
  strip_jsonc "$1" | jq -r "$2"
}

# The config root as declared, or empty when the key is gone. Detector for the
# devcontainer half of the fix.
config_root() {
  query "$1" '.containerEnv.CLAUDE_CONFIG_DIR // empty'
}

# Every absolute path a registry file records under the container-only root.
# Non-empty means the registry was last written from a container that used
# /home/node/.claude as its config root — the defect this task removes.
container_rooted_paths() {
  jq -r '.. | strings | select(startswith("/home/node/"))' "$1"
}

@test "CLAUDE_CONFIG_DIR is the host .claude path in both copies" {
  local f root
  for f in "$LIVE" "$TEMPLATE"; do
    root="$(config_root "$f")"
    [ "$root" = '${localEnv:HOME}/.claude' ] || {
      echo "$f declares CLAUDE_CONFIG_DIR=$root"
      echo "container runs will write that root into the shared plugin registries"
      return 1
    }
  done
}

@test "CLAUDE_CONFIG_DIR is not rooted at the container-only /home/node" {
  local f
  for f in "$LIVE" "$TEMPLATE"; do
    # Stated separately from the positive assertion: a future rewrite that
    # invents a third root (say a container-local volume) must fail this too,
    # because it would again leave the host unable to read what the container
    # wrote.
    [[ "$(config_root "$f")" != /home/node/* ]]
  done
}

@test "the config root is backed by a bind, so it exists in the container" {
  local f
  for f in "$LIVE" "$TEMPLATE"; do
    # Without the bind at that exact target, Docker/Claude Code would create an
    # empty directory there and the container would start with a blank config.
    [ -n "$(query "$f" \
      '.mounts[] | select(test("target=\\$\\{localEnv:HOME\\}/\\.claude(,|$)"))')" ]
  done
}

@test "the /home/node/.claude bind stays as the \$HOME alias" {
  local f
  for f in "$LIVE" "$TEMPLATE"; do
    # $HOME is /home/node in the container, so anything that ignores
    # CLAUDE_CONFIG_DIR and reads ~/.claude must still land on the same bytes.
    [ -n "$(query "$f" '.mounts[] | select(test("target=/home/node/\\.claude(,|$)"))')" ]
  done
}

@test "the config root carries a comment naming the registry consequence" {
  local f comments
  for f in "$LIVE" "$TEMPLATE"; do
    # Otherwise the host-shaped value reads as a pointless indirection of
    # /home/node/.claude and gets "simplified" back.
    comments="$(grep -E '^[[:space:]]*//' "$f")"
    grep -qi 'installLocation' <<< "$comments" || {
      echo "$f has no comment naming installLocation"
      return 1
    }
  done
}

@test "live and template devcontainer.json stay byte-identical" {
  run diff "$LIVE" "$TEMPLATE"
  [ "$status" -eq 0 ]
}

@test "the config-root assertion fails against the pre-fix copy of each file" {
  # Mutation check for the devcontainer half: derive the pre-fix file by
  # putting the old container root back, and assert the detector reports it.
  local f pre tmp
  tmp="$(mktemp -d)"
  for f in "$LIVE" "$TEMPLATE"; do
    pre="$tmp/pre-fix-$(basename "$(dirname "$f")").json"
    sed 's@"CLAUDE_CONFIG_DIR": "${localEnv:HOME}/.claude"@"CLAUDE_CONFIG_DIR": "/home/node/.claude"@' \
      "$f" > "$pre"

    # The mutation actually landed and left valid JSONC behind — a green suite
    # cannot be explained away by a no-op sed or a broken scratch file.
    strip_jsonc "$pre" | jq -e . > /dev/null
    [ "$(config_root "$pre")" = "/home/node/.claude" ]

    # ... and the detector calls it out, while the real file passes.
    [[ "$(config_root "$pre")" == /home/node/* ]]
    [[ "$(config_root "$f")" != /home/node/* ]]
  done
  rm -rf "$tmp"
}

@test "the registry detector fires on a container-rooted registry" {
  # Mutation check for the registry half, against the shape actually observed
  # on the host on 2026-09-27 (11 of 12 marketplaces relocated in one batch).
  local tmp
  tmp="$(mktemp -d)"
  cat > "$tmp/known_marketplaces.json" <<'EOF'
{
  "dddpaul-ralph": {
    "source": { "source": "git", "url": "https://github.com/dddpaul/ralph.git" },
    "installLocation": "/home/node/.claude/plugins/marketplaces/dddpaul-ralph"
  }
}
EOF
  [ -n "$(container_rooted_paths "$tmp/known_marketplaces.json")" ]

  # And it stays quiet on the host-shaped equivalent, so it is not matching
  # everything in sight.
  sed 's@/home/node/@/Users/paul/@' "$tmp/known_marketplaces.json" \
    > "$tmp/repaired.json"
  [ -z "$(container_rooted_paths "$tmp/repaired.json")" ]
  rm -rf "$tmp"
}

@test "the shared plugin registries hold no container-rooted path" {
  # The live invariant, checked wherever a real config is reachable — on the
  # host after a devcontainer run, and inside the container itself. Skipped on
  # a machine whose own config root really is under /home/node (a Linux host
  # with user "node"), where those paths are local and correct.
  local root f found
  root="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  case "$root" in
    /home/node/*) skip "local config root is itself under /home/node: $root" ;;
  esac
  [ -d "$root/plugins" ] || skip "no plugin registry at $root/plugins"

  for f in "$root/plugins/known_marketplaces.json" \
           "$root/plugins/installed_plugins.json"; do
    [ -f "$f" ] || continue
    found="$(container_rooted_paths "$f")"
    [ -z "$found" ] || {
      echo "$f records container-only paths; the host cannot resolve them:"
      echo "$found"
      return 1
    }
  done
}
