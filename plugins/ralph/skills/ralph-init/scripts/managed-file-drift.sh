#!/usr/bin/env bash
# Report ralph-init managed files in a project that are behind the installed
# plugin's templates.
#
#   managed-file-drift.sh check <project-dir>
#       Prints one "<path>: outdated" or "<path>: missing" line per managed file
#       whose content differs from the shipped template, or that is absent.
#       Exit 0 = clean, 1 = drift found.
#   managed-file-drift.sh list
#       Prints the managed paths, one per line, in the Upgrade U2 order.
#   Exit 2 = usage error, unreadable project directory or template tree.
#
# The comparison is content only — a project records no ralph-init version, and
# a stamp would claim what a diff shows. Templates come from
# $CLAUDE_PLUGIN_ROOT (the plugin's root directory); when it is unset, from the
# plugin this script ships in. The rules are the ones ralph-init SKILL.md
# Upgrade U2 lists, and tests/python/test_managed_file_drift.py pins the table
# below against that list:
#
#   exact     — byte-identical to the template.
#   above:<h> — only the lines above the first line equal to <h> are compared;
#               a project file without that line is outdated.
#   hooks     — every templates/claude/hooks/*-guard.sh and task-validator.sh
#               must match .claude/hooks/<name>.sh.
#
# Gates skip a row silently: "devcontainer" without a .devcontainer/ directory,
# "obsidian" without .obsidian/ (Code-only), "git" without a .git/ directory.
# .devcontainer/Dockerfile (assembled) and .gitignore (append-only) are never
# compared. Project-owned files — .claude/task-reviewer-rules.md above all —
# are not in the table and are never read.
set -euo pipefail

usage() {
  echo "usage: managed-file-drift.sh check <project-dir> | list" >&2
  exit 2
}

# path|template (plugin-root-relative)|rule|gate
table() {
  cat <<'ROWS'
ralph.sh|skills/ralph-init/templates/root/ralph.sh|exact|-
refine.sh|skills/ralph-init/templates/root/refine.sh|exact|-
CLAUDE.md|skills/ralph-init/templates/root/CLAUDE.md|above:## Project-Specific|-
.git/hooks/post-commit|skills/ralph-init/templates/git-hooks/post-commit|exact|git
.git/hooks/commit-msg|skills/ralph-init/templates/git-hooks/commit-msg|exact|git
.git/hooks/pre-commit|skills/ralph-init/templates/git-hooks/pre-commit|exact|git
.claude/settings.json|skills/ralph-init/templates/claude/settings.json|exact|-
.claude/hooks/|skills/ralph-init/templates/claude/hooks/|hooks|-
.claude/settings.local.json|skills/ralph-init/templates/claude/settings.local.json|exact|-
.devcontainer/devcontainer.json|skills/ralph-init/templates/devcontainer/devcontainer.json|exact|devcontainer
.devcontainer/init-firewall.sh|skills/ralph-init/templates/devcontainer/init-firewall.sh|exact|devcontainer
.claude/brainstorm-rules.md|skills/ralph-init/templates/claude/brainstorm-rules.md|above:## Project additions|-
.claude/task-reviewer-rules.docs.md|skills/ralph-init/rules/task-reviewer-rules.docs.md|exact|obsidian
.devcontainer/container-settings.local.json|skills/ralph-init/templates/devcontainer/container-settings.local.json|exact|devcontainer
ROWS
}

# Print the lines of $2 above the first line equal to $1.
above() {
  awk -v h="$1" '$0 == h { exit } { print }' "$2"
}

# Compare project file $1 with template $2 under rule $3; print a drift line.
compare() {
  local path=$1 tmpl=$2 rule=$3 file=$project/$1
  [ -r "$tmpl" ] || { echo "managed-file-drift: cannot read $tmpl" >&2; exit 2; }
  if [ ! -e "$file" ]; then
    echo "$path: missing"
  elif [ "$rule" = exact ]; then
    cmp -s "$file" "$tmpl" || echo "$path: outdated"
  else
    local heading=${rule#above:}
    if ! grep -Fxq -- "$heading" "$file" || ! cmp -s <(above "$heading" "$file") <(above "$heading" "$tmpl"); then
      echo "$path: outdated"
    fi
  fi
}

[ $# -ge 1 ] || usage
case $1 in
  list)
    [ $# -eq 1 ] || usage
    table | cut -d'|' -f1
    exit 0
    ;;
  check) [ $# -eq 2 ] || usage ;;
  *) usage ;;
esac
project=${2%/}
[ -d "$project" ] && [ -r "$project" ] || { echo "managed-file-drift: cannot read $project" >&2; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
root=${CLAUDE_PLUGIN_ROOT:-$here/../../..}
[ -d "$root/skills/ralph-init/templates" ] || {
  echo "managed-file-drift: no ralph-init templates under $root" >&2
  exit 2
}

report=$(
  table | while IFS='|' read -r path tmpl rule gate; do
    case $gate in
      git) [ -d "$project/.git" ] || continue ;;
      devcontainer) [ -d "$project/.devcontainer" ] || continue ;;
      obsidian) [ -d "$project/.obsidian" ] || continue ;;
    esac
    if [ "$rule" = hooks ]; then
      for hook in "$root/$tmpl"*-guard.sh "$root/${tmpl}task-validator.sh"; do
        compare "$path${hook##*/}" "$hook" exact
      done
    else
      compare "$path" "$root/$tmpl" "$rule"
    fi
  done
)
[ -n "$report" ] || exit 0
printf '%s\n' "$report"
exit 1
