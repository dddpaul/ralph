#!/bin/bash
# Disable Claude Code sandbox in devcontainer (iptables firewall provides network isolation)
SETTINGS="/workspace/.claude/settings.local.json"
if [ -f "$SETTINGS" ]; then
  PATCHED=$(mktemp)
  jq '.sandbox.enabled = false' "$SETTINGS" > "$PATCHED"
  mount --bind "$PATCHED" "$SETTINGS"
fi
