#!/bin/bash
# run.sh — Run one plugin guard hook behind the project's ownership marker.
# Usage: run.sh <guard>        (hook input JSON on stdin)
#
# Every entry in hooks.json calls this dispatcher. The guard runs only when
# .claude/ralph.json at the session's canonical git root has "pluginHooks":
# true and does not list the guard in "localGuards"; otherwise this exits 0,
# so a project that has not migrated keeps only its legacy .claude/hooks/
# wiring and is never checked twice.
#
# The root is `git rev-parse --show-toplevel` from CLAUDE_PROJECT_DIR, made
# canonical with `pwd -P`: a session started in a subdirectory finds its
# root, and a nested repository is its own root, so its own marker (or none)
# decides. The guard gets the hook input unchanged, runs from the payload's
# cwd (where Claude ran the command), sees RALPH_PROJECT_ROOT for project
# paths, and its exit code is the dispatcher's.

unset CDPATH

guard=${1:-}
case "$guard" in
  '' | *[!a-z-]*)
    echo "ralph hooks: invalid guard name '$guard'" >&2
    exit 1
    ;;
esac
script="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/$guard.sh"
if [ ! -x "$script" ]; then
  echo "ralph hooks: no executable guard at $script" >&2
  exit 1
fi

root=$(cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) || exit 0
root=$(cd "$root" 2>/dev/null && pwd -P) || exit 0
marker="$root/.claude/ralph.json"
[ -f "$marker" ] || exit 0

# jq: PATH first, else the clone's `git config ralph.jq`; the guards need it too.
jq_bin=$(command -v jq 2>/dev/null) || jq_bin=$(git -C "$root" config ralph.jq 2>/dev/null) || jq_bin=
if [ -z "$jq_bin" ] || [ ! -x "$jq_bin" ]; then
  echo "ralph hooks: jq not found (PATH or git config ralph.jq); $guard skipped" >&2
  exit 1
fi
case ":$PATH:" in *":$(dirname "$jq_bin"):"*) ;; *) PATH="$(dirname "$jq_bin"):$PATH" ;; esac

state=$("$jq_bin" -r --arg g "$guard" '
  if .pluginHooks != true then "off"
  elif ((.localGuards // []) | type == "array" and index($g) != null) then "local"
  else "on" end' "$marker" 2>/dev/null) || {
  echo "ralph hooks: cannot read $marker; $guard skipped" >&2
  exit 1
}
[ "$state" = on ] || exit 0

# Keep the input byte-for-byte, trailing newlines included.
input=$(cat; printf x)
input=${input%x}

cwd=$(printf '%s' "$input" | "$jq_bin" -r '.cwd // empty' 2>/dev/null)
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  cd "$cwd" || exit 1
fi

RALPH_PROJECT_ROOT=$root
export RALPH_PROJECT_ROOT PATH
printf '%s' "$input" | "$script"
