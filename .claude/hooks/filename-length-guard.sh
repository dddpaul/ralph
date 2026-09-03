#!/bin/bash
# filename-length-guard.sh — Reject staged paths whose name components exceed
# the 125-byte filename cap.
#
# Called from .git/hooks/pre-commit. Lives here (not inlined into the hook) so
# the logic is tracked, testable, and mirrored into the ralph-init templates.
#
# Why 125 bytes: this repo replicates to a Linux ecryptfs volume whose per-name
# limit is ~140-143 bytes. Syncthing transfers each file under a temp name
# `.syncthing.<name>.tmp` (+15 bytes), so a committed name over 125 bytes never
# lands on the sync target. The same cap keeps names inside Windows MAX_PATH
# budgets and tar/zip round-trips.
#
# Every path COMPONENT is measured, not just the basename: a long directory
# segment breaks sync exactly the same way.

set -euo pipefail

export LC_ALL=C   # so ${#name} counts BYTES, not characters — ecryptfs limits
                  # bytes, and a UTF-8 locale would under-count multibyte names.

MAX=125

# --diff-filter=ACMR: added / copied / modified / renamed only. Deletions are
# excluded on purpose — the commit that RENAMES an over-limit path stages the
# deletion of the old long name, and an unfiltered scan would make that commit
# block itself.
#
# core.quotePath=false: emit raw UTF-8 bytes instead of C-style \320\271
# escapes, which would inflate every multibyte name to 4 bytes per byte.
staged=$(git -c core.quotePath=false diff --cached --name-only --diff-filter=ACMR)
[ -z "$staged" ] && exit 0

violations=""
while IFS= read -r path; do
  [ -z "$path" ] && continue
  rest="$path"
  while [ -n "$rest" ]; do
    comp="${rest%%/*}"
    case "$rest" in
      */*) rest="${rest#*/}" ;;
      *)   rest="" ;;
    esac
    [ -z "$comp" ] && continue
    len=${#comp}
    if [ "$len" -gt "$MAX" ]; then
      violations="${violations}  ${path}
    component: ${comp}
    ${len} bytes ($((len - MAX)) over the ${MAX}-byte cap)
"
    fi
  done
done <<< "$staged"

[ -z "$violations" ] && exit 0

{
  echo "BLOCKED: staged path has a name component over the ${MAX}-byte filename cap."
  printf '%s' "$violations"
  echo "Rename before committing:"
  echo "  backlog/tasks/task-<id> - ...   ->  backlog task edit <id> -t \"<shorter title>\""
  echo "  any other path                  ->  git mv \"<old>\" \"<new>\""
  echo "Why ${MAX}: the ecryptfs sync target caps names at ~140 bytes and Syncthing"
  echo "adds 15 for its .syncthing.<name>.tmp transfer name."
} >&2

exit 1
