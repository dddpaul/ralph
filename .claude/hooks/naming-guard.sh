#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // empty')
command=$(echo "$input" | jq -r '.tool_input.command // empty')

[[ "$tool" == "Bash" ]] || exit 0

if echo "$command" | grep -qE '^backlog task create\b'; then
  title=$(echo "$command" | sed -n 's/^backlog task create[[:space:]]*"\([^"]*\)".*/\1/p')
  if [[ -z "$title" ]]; then
    title=$(echo "$command" | sed -n "s/^backlog task create[[:space:]]*'\([^']*\)'.*/\1/p")
  fi
  if [[ -n "$title" ]] && LC_ALL=C grep -q '[^[:print:][:space:]]' <<< "$title"; then
    echo "BLOCKED: title/branch must be ASCII English (filenames are derived from titles). Put translations in -d or --ac." >&2
    exit 2
  fi
fi

if echo "$command" | grep -qE '^git checkout -b\b'; then
  branch_name=$(echo "$command" | sed -n 's/^git checkout -b[[:space:]]*\([^[:space:]]*\).*/\1/p')
  if [[ -n "$branch_name" ]] && LC_ALL=C grep -q '[^[:print:][:space:]]' <<< "$branch_name"; then
    echo "BLOCKED: title/branch must be ASCII English (filenames are derived from titles). Put translations in -d or --ac." >&2
    exit 2
  fi
fi

exit 0
