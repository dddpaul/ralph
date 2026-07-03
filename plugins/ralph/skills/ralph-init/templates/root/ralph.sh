#!/usr/bin/env bash
# Thin shim — locates the Ralph orchestrator wherever the plugin is installed and
# execs it. A detached `nohup ./ralph.sh` has no ${CLAUDE_PLUGIN_ROOT}, so the
# orchestrator is resolved via a 5-tier precedence (see
# design/ralph-marketplace-prd.md US-004):
#   1. $RALPH_ORCHESTRATOR                         explicit override
#   2. in-repo plugin source                       this marketplace repo checked out
#   3. legacy ~/.claude/skills install             pre-marketplace /ralph-sync layout
#   4. newest marketplace plugin-cache install     /plugin install ...
#   5. clear error                                 plugin not installed
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
export RALPH_PROJECT_ROOT

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

# Print the resolved orchestrator path on stdout; return 1 if none is found.
resolve_orchestrator() {
  # Tier 1: explicit override.
  if [ -n "${RALPH_ORCHESTRATOR:-}" ] && [ -f "${RALPH_ORCHESTRATOR:-}" ]; then
    printf '%s\n' "$RALPH_ORCHESTRATOR"
    return 0
  fi

  # Tier 2: in-repo plugin source (this marketplace repo checked out).
  local in_repo="$RALPH_PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py"
  if [ -f "$in_repo" ]; then
    printf '%s\n' "$in_repo"
    return 0
  fi

  # Tier 3: legacy user-global install (pre-marketplace /ralph-sync layout).
  local legacy="$CLAUDE_DIR/skills/ralph-run/scripts/ralph_orchestrator.py"
  if [ -f "$legacy" ]; then
    printf '%s\n' "$legacy"
    return 0
  fi

  # Tier 4: newest marketplace plugin-cache install. Layout:
  #   <cfg>/plugins/cache/<marketplace>/ralph/<ref>/skills/ralph-run/scripts/ralph_orchestrator.py
  local cached
  cached="$(
    shopt -s nullglob
    matches=("$CLAUDE_DIR"/plugins/cache/*/ralph/*/skills/ralph-run/scripts/ralph_orchestrator.py)
    [ "${#matches[@]}" -gt 0 ] && printf '%s\n' "${matches[@]}" | sort -V | tail -n 1
  )"
  if [ -n "$cached" ] && [ -f "$cached" ]; then
    printf '%s\n' "$cached"
    return 0
  fi

  return 1
}

if ! ORCHESTRATOR="$(resolve_orchestrator)"; then
  {
    echo "ERROR: could not locate ralph_orchestrator.py."
    echo "Install the Ralph plugin, then retry:"
    echo "  /plugin marketplace add dddpaul/ralph"
    echo "  /plugin install ralph@dddpaul-ralph"
    echo "Or set RALPH_ORCHESTRATOR to the orchestrator path."
  } >&2
  exit 1
fi

exec uv run "$ORCHESTRATOR" "$@"
