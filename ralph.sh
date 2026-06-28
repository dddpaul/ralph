#!/usr/bin/env bash
# Thin shim — the real orchestrator lives under ~/.claude/skills/ralph-run/scripts/
# Install/update via /ralph-sync.
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CANONICAL_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts"
export RALPH_PROJECT_ROOT
exec uv run "$CANONICAL_DIR/ralph_orchestrator.py" "$@"
