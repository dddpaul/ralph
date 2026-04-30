#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // empty')
command=$(echo "$input" | jq -r '.tool_input.command // empty')

[[ "$tool" == "Bash" ]] || exit 0

case "$command" in
  git\ commit*|gh\ pr\ create*) ;;
  *) exit 0 ;;
esac

if echo "$command" | grep -qiE 'Co-Authored-By|Generated with Claude Code'; then
  echo "BLOCKED: forbidden trailer/heading. Remove Co-Authored-By, Generated-with, and Test plan sections." >&2
  exit 2
fi

if echo "$command" | grep -qE '##[[:space:]]*Test [Pp]lan'; then
  echo "BLOCKED: forbidden trailer/heading. Remove Co-Authored-By, Generated-with, and Test plan sections." >&2
  exit 2
fi

exit 0
