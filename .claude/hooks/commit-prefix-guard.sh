#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // empty')
command=$(echo "$input" | jq -r '.tool_input.command // empty')

[[ "$tool" == "Bash" ]] || exit 0

echo "$command" | grep -qE '^git commit\b' || exit 0

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if ! echo "$branch" | grep -qE '^task-[0-9]+'; then
  exit 0
fi

task_id=$(echo "$branch" | grep -oE '^task-[0-9]+' | sed 's/task-//')

msg=$(echo "$command" | sed -n 's/.*-m[[:space:]]*"\(.*\)".*/\1/p')
if [[ -z "$msg" ]]; then
  msg=$(echo "$command" | sed -n "s/.*-m[[:space:]]*'\(.*\)'.*/\1/p")
fi
if [[ -z "$msg" ]]; then
  msg=$(echo "$command" | sed -n '/cat <</{s/.*//;n;s/^[[:space:]]*//;p;q;}')
fi

if echo "$msg" | grep -qiE '^Merge branch'; then
  exit 0
fi

if ! echo "$msg" | grep -qE "^task-${task_id}: "; then
  echo "BLOCKED: commit message on task-${task_id} branch must start with \`task-${task_id}: \`." >&2
  exit 2
fi

exit 0
