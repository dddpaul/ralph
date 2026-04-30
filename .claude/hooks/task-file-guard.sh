#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // empty')

case "$tool" in
  Edit|Write) ;;
  *) exit 0 ;;
esac

path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

if echo "$path" | grep -qE 'backlog/tasks/.*\.md$'; then
  echo "BLOCKED: do not edit task files directly. Use backlog task edit (run \`backlog task edit --help\` for syntax)." >&2
  exit 2
fi

exit 0
