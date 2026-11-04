#!/usr/bin/env bash
# Thin shim — locates the ralph-refine orchestrator wherever the plugin is
# installed and execs it. A detached `nohup ./refine.sh` has no
# ${CLAUDE_PLUGIN_ROOT}, so the orchestrator is resolved via a 5-tier precedence
# mirroring ralph.sh (see design/ralph-refine-prd.md US-006 and
# design/ralph-marketplace-prd.md US-004; tier 4 per
# design/plugin-delivered-project-files-prd.md US-001):
#   1. $REFINE_ORCHESTRATOR                        explicit override
#   2. in-repo plugin source                       this marketplace repo checked out
#   3. legacy ~/.claude/skills install             pre-marketplace /ralph-sync layout
#   4. the registered plugin install               installed_plugins.json
#   5. clear error                                 plugin not installed
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
export RALPH_PROJECT_ROOT

# >>> ralph-resolve-plugin >>>
# ralph_resolve_plugin <dir> <relpath>
#   Print <installPath>/<relpath> for the ralph@dddpaul-ralph install that Claude
#   Code registered for the clone holding <dir>; on failure print one reason on
#   stderr and return 1. A project-scope entry whose projectPath is the clone's
#   identity (git config ralph.projectPath, else the main worktree root) wins
#   over the user-scope entry (design/plugin-delivered-project-files-prd.md US-001).
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

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

# Print the resolved orchestrator path on stdout; return 1 if none is found.
resolve_orchestrator() {
  # Tier 1: explicit override.
  if [ -n "${REFINE_ORCHESTRATOR:-}" ] && [ -f "${REFINE_ORCHESTRATOR:-}" ]; then
    printf '%s\n' "$REFINE_ORCHESTRATOR"
    return 0
  fi

  # Tier 2: in-repo plugin source (this marketplace repo checked out).
  local in_repo="$RALPH_PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts/refine_orchestrator.py"
  if [ -f "$in_repo" ]; then
    printf '%s\n' "$in_repo"
    return 0
  fi

  # Tier 3: legacy user-global install (pre-marketplace /ralph-sync layout).
  local legacy="$CLAUDE_DIR/skills/ralph-run/scripts/refine_orchestrator.py"
  if [ -f "$legacy" ]; then
    printf '%s\n' "$legacy"
    return 0
  fi

  # Tier 4: the install Claude Code registered for this project or user.
  ralph_resolve_plugin "$RALPH_PROJECT_ROOT" skills/ralph-run/scripts/refine_orchestrator.py
}

if ! ORCHESTRATOR="$(resolve_orchestrator)"; then
  {
    echo "ERROR: could not locate refine_orchestrator.py."
    echo "Install the Ralph plugin, then retry:"
    echo "  /plugin marketplace add dddpaul/ralph"
    echo "  /plugin install ralph@dddpaul-ralph"
    echo "Or set REFINE_ORCHESTRATOR to the orchestrator path."
  } >&2
  exit 1
fi

exec uv run "$ORCHESTRATOR" "$@"
