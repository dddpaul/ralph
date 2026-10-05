#!/usr/bin/env bash
# Report and retire the per-project copy of the shared docs reviewer rules,
# .claude/task-reviewer-rules.docs.md, that ralph-init used to write.
#
#   legacy-docs-rules.sh check <project-dir>
#       Prints one line describing the copy when it exists and exits 1; exits 0
#       with no output when it does not. The line says whether the copy matches
#       the rules bundle shipped in the installed plugin or differs from it (an
#       older shipped version or local edits — the two cannot be told apart).
#   legacy-docs-rules.sh retire <project-dir> <answer>
#       Removes the copy iff <answer> is y or yes (any case); any other answer,
#       the empty one included, keeps it. Prints "removed" or "kept" ("absent"
#       when the answer is yes but there is no copy).
#   Exit 2 = usage error or unreadable project directory.
#
# The task-reviewer agent reads the bundle from the plugin root and never this
# copy, so a project that keeps it is unaffected; removing it is housekeeping
# the operator must agree to, never a silent delete. The bundle comes from
# $CLAUDE_PLUGIN_ROOT (the plugin's root directory); when it is unset, from the
# plugin this script ships in.
set -euo pipefail

COPY=.claude/task-reviewer-rules.docs.md

usage() {
  echo "usage: legacy-docs-rules.sh check <project-dir> | retire <project-dir> <answer>" >&2
  exit 2
}

[ $# -ge 2 ] || usage
case $1 in
  check) [ $# -eq 2 ] || usage ;;
  retire) [ $# -eq 3 ] || usage ;;
  *) usage ;;
esac
project=${2%/}
[ -d "$project" ] && [ -r "$project" ] || { echo "legacy-docs-rules: cannot read $project" >&2; exit 2; }
file=$project/$COPY

if [ "$1" = retire ]; then
  case $(printf '%s' "$3" | tr '[:upper:]' '[:lower:]') in
    y | yes)
      if [ -e "$file" ]; then
        rm -f -- "$file"
        echo removed
      else
        echo absent
      fi
      ;;
    *) echo kept ;;
  esac
  exit 0
fi

[ -e "$file" ] || exit 0
here=$(cd "$(dirname "$0")" && pwd)
root=${CLAUDE_PLUGIN_ROOT:-$here/../../..}
bundle=$root/skills/ralph-init/rules/task-reviewer-rules.docs.md
if [ ! -r "$bundle" ]; then
  echo "$COPY: legacy copy (shipped rules not found under $root, not compared)"
elif cmp -s "$file" "$bundle"; then
  echo "$COPY: legacy copy, matches the shipped rules"
else
  echo "$COPY: legacy copy, differs from the shipped rules (an older shipped version or local edits)"
fi
exit 1
