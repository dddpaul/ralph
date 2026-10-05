#!/usr/bin/env bash
# Print a devcontainer.json template with the project's own runArgs kept.
#
#   merge-runargs.sh <template> <project-file>
#
# Every line is the template's except its single-line "runArgs" array, which
# lists the template's elements followed by each element of the project file's
# single-line "runArgs" array that the template lacks, in project order. A
# project file that is absent, or whose "runArgs" is not one line, adds
# nothing. Upgrade U4 writes this output over .devcontainer/devcontainer.json,
# and managed-file-drift.sh calls the file current when it equals this output.
# Exit 2 = usage error or unreadable template.
set -euo pipefail

[ $# -eq 2 ] || { echo "usage: merge-runargs.sh <template> <project-file>" >&2; exit 2; }
tmpl=$1 file=$2
[ -r "$tmpl" ] || { echo "merge-runargs: cannot read $tmpl" >&2; exit 2; }
key='^[[:space:]]*"runArgs":[[:space:]]*\[.*\]'

# Print the quoted elements of the one single-line runArgs array in $1.
elements() {
  [ -r "$1" ] || return 0
  [ "$(grep -cE "$key" "$1")" = 1 ] || return 0
  grep -E "$key" "$1" | sed -e 's/^[^[]*\[//' -e 's/\][^]]*$//' | grep -o '"[^"]*"' || true
}

n=$(grep -nE "$key" "$tmpl" | cut -d: -f1)
case $n in
  (*[!0-9]* | '') cat "$tmpl"; exit 0 ;;
esac
own=$(elements "$tmpl")
array=$(
  { printf '%s\n' "$own"
    elements "$file" | while IFS= read -r el; do
      printf '%s\n' "$own" | grep -Fxq -- "$el" || printf '%s\n' "$el"
    done
  } | awk 'NF && !seen[$0]++ { printf "%s%s", (n++ ? ", " : ""), $0 }'
)
line=$(sed -n "${n}p" "$tmpl")
head -n $((n - 1)) "$tmpl"
printf '%s[%s]%s\n' "${line%%\[*}" "$array" "${line##*\]}"
tail -n +$((n + 1)) "$tmpl"
