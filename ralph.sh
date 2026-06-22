#!/usr/bin/env bash
# Thin shim — the real scripts live under ~/.claude/skills/ralph-run/scripts/
# Install/update via /ralph-sync. Dispatch by RALPH_IMPL env var (default: python).
# Set RALPH_IMPL=bash to fall back to the legacy bash orchestrator during the rollback window.
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CANONICAL_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts"
export RALPH_PROJECT_ROOT
if [ "${RALPH_IMPL:-python}" = "bash" ]; then
  exec "$CANONICAL_DIR/ralph.sh" "$@"
fi
exec uv run "$CANONICAL_DIR/ralph_orchestrator.py" "$@"
