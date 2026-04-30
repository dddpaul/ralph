#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // empty')
command=$(echo "$input" | jq -r '.tool_input.command // empty')

[[ "$tool" == "Bash" ]] || exit 0

echo "$command" | grep -q 'backlog task edit' || exit 0

if echo "$command" | grep -qE ' --notes([= ]|$)' && ! echo "$command" | grep -qE ' --append-notes'; then
  echo "BLOCKED: --notes overwrites the Notes section and destroys commit hashes. Use --append-notes instead." >&2
  exit 2
fi

exit 0
