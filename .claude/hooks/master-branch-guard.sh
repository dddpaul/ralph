#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // empty')

case "$tool" in
  Edit|Write) ;;
  *) exit 0 ;;
esac

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
[[ "$branch" == "master" ]] || exit 0

path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

case "$path" in
  */.claude/*|.claude/*) exit 0 ;;
esac

[[ "$(basename "$path")" == ".gitignore" ]] && exit 0

echo "BLOCKED: no active task branch. Create a backlog task and \`git checkout -b task-<id>-<desc> master\` first." >&2
exit 2
