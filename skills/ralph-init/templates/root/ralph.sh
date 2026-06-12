#!/usr/bin/env bash
# Thin shim — the real script lives at ~/.claude/skills/ralph-run/scripts/ralph.sh
# Install/update via /ralph-sync
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" \
  exec "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh" "$@"
