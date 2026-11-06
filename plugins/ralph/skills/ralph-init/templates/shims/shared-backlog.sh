#!/usr/bin/env bash
# Ralph shared-backlog shim (TASK-310). ralph-init installs this file, unedited,
# as scripts/shared-backlog.sh in a project that opts in to the shared-backlog
# protocol. It execs plugins/ralph/scripts/shared-backlog.sh from the installed
# ralph plugin, so the protocol arrives with a plugin update
# (design/plugin-delivered-project-files-prd.md US-016). Replace this file only
# through ralph-init.

# >>> ralph-resolve-plugin >>>
# ralph_resolve_plugin <dir> <relpath>
#   Print <installPath>/<relpath> for the ralph@dddpaul-ralph install that Claude
#   Code registered for the clone holding <dir>; on failure print one reason on
#   stderr and return 1. Like Claude Code (observed on 2.1.309), it takes the
#   first entry in registry order that applies: a user-scope entry, or a project-
#   or local-scope entry whose projectPath is the clone's identity (git config
#   ralph.projectPath, else the main worktree root)
#   (design/plugin-delivered-project-files-prd.md US-001).
ralph_resolve_plugin() {
  local dir="$1" rel="$2" common root id jq cfg reg ver sel count install
  common="$(unset CDPATH; cd -- "$dir" 2>/dev/null && c="$(git rev-parse --git-common-dir 2>/dev/null)" && cd -- "$c" && pwd -P)"
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
    [.plugins["ralph@dddpaul-ralph"][]?
      | select(.scope == "user" or ((.scope == "project" or .scope == "local") and .projectPath == $id))] as $c
    | "\($c | length) \($c[0].installPath // "")"' "$reg" 2>/dev/null)"
  count="${sel%% *}"
  install="${sel#* }"
  case "$count" in
    0)
      echo "ralph: plugin lookup: ralph@dddpaul-ralph has no user-scope entry and no project- or local-scope entry for $id in $reg" >&2
      return 1
      ;;
    *[!0-9]* | '')
      echo "ralph: plugin lookup: cannot read the ralph@dddpaul-ralph entries in $reg" >&2
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

if script="$(ralph_resolve_plugin "$PWD" scripts/shared-backlog.sh)"; then
  exec bash "$script" "$@"
fi
echo "shared-backlog: the ralph plugin cannot be resolved (reason above); install or update the ralph plugin" >&2
exit 1
