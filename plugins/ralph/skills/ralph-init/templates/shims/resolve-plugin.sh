# Source of truth for the Ralph plugin registry resolver. ralph.sh, refine.sh and
# every shim template under this directory embed the block between the two
# marker lines byte for byte; tests/python/test_resolve_plugin.py fails on drift.
# >>> ralph-resolve-plugin >>>
# ralph_resolve_plugin <dir> <relpath>
#   Print <installPath>/<relpath> for the ralph@dddpaul-ralph install that Claude
#   Code registered for the clone holding <dir>; on failure print one reason on
#   stderr and return 1. A project-scope entry whose projectPath is the clone's
#   identity (git config ralph.projectPath, else the main worktree root) wins
#   over the user-scope entry (design/plugin-delivered-project-files-prd.md US-001).
ralph_resolve_plugin() {
  local dir="$1" rel="$2" common root id jq cfg reg ver sel count install
  common="$(cd "$dir" 2>/dev/null && c="$(git rev-parse --git-common-dir 2>/dev/null)" && cd "$c" && pwd -P)"
  if [ -z "$common" ]; then
    echo "ralph: plugin lookup: $dir is not inside a git work tree" >&2
    return 1
  fi
  case "$common" in
    */.git) root="${common%/.git}" ;;
    *)
      echo "ralph: plugin lookup: separate git dir layout is not supported (git common dir $common is not <root>/.git)" >&2
      return 1
      ;;
  esac
  [ -n "$root" ] || root=/
  id="$(git -C "$dir" config ralph.projectPath 2>/dev/null)"
  [ -n "$id" ] || id="$root"
  if command -v jq >/dev/null 2>&1; then
    jq=jq
  else
    jq="$(git -C "$dir" config ralph.jq 2>/dev/null)"
    if [ -z "$jq" ] || [ ! -x "$jq" ]; then
      echo "ralph: plugin lookup: jq is not on PATH and git config ralph.jq names no executable" >&2
      return 1
    fi
  fi
  cfg="${CLAUDE_CONFIG_DIR:-}"
  [ -n "$cfg" ] || cfg="$(git -C "$dir" config ralph.claudeConfigDir 2>/dev/null)"
  [ -n "$cfg" ] || cfg="$HOME/.claude"
  reg="$cfg/plugins/installed_plugins.json"
  if [ ! -f "$reg" ]; then
    echo "ralph: plugin lookup: plugin registry $reg not found" >&2
    return 1
  fi
  if ! ver="$("$jq" -r '.version // "none"' "$reg" 2>/dev/null)"; then
    echo "ralph: plugin lookup: plugin registry $reg is not valid JSON" >&2
    return 1
  fi
  if [ "$ver" != 2 ]; then
    echo "ralph: plugin lookup: plugin registry $reg has version $ver, expected 2" >&2
    return 1
  fi
  sel="$("$jq" -r --arg id "$id" '
    [.plugins["ralph@dddpaul-ralph"][]?] as $all
    | [$all[] | select(.scope == "project" and .projectPath == $id)] as $proj
    | (if ($proj | length) > 0 then $proj else [$all[] | select(.scope == "user")] end) as $c
    | "\($c | length) \($c[0].installPath // "")"' "$reg" 2>/dev/null)"
  count="${sel%% *}"
  install="${sel#* }"
  case "$count" in
    1) ;;
    0)
      echo "ralph: plugin lookup: ralph@dddpaul-ralph has no project-scope entry for $id and no user-scope entry in $reg" >&2
      return 1
      ;;
    *[!0-9]* | '')
      echo "ralph: plugin lookup: cannot read the ralph@dddpaul-ralph entries in $reg" >&2
      return 1
      ;;
    *)
      echo "ralph: plugin lookup: $count candidate ralph@dddpaul-ralph entries for $id in $reg" >&2
      return 1
      ;;
  esac
  if [ -z "$install" ]; then
    echo "ralph: plugin lookup: the ralph@dddpaul-ralph entry in $reg has no installPath" >&2
    return 1
  fi
  if [ ! -d "$install" ]; then
    echo "ralph: plugin lookup: installPath $install does not exist" >&2
    return 1
  fi
  if [ ! -f "$install/$rel" ]; then
    echo "ralph: plugin lookup: $install/$rel not found in the installed plugin" >&2
    return 1
  fi
  printf '%s\n' "$install/$rel"
}
# <<< ralph-resolve-plugin <<<
