#!/usr/bin/env bash
# Report ralph-init managed files in a project that are behind the installed
# plugin's templates and, for the legacy copies of a project that is not yet
# migrated to plugin hooks, the plugin's own hooks/ and git-hooks/.
#
#   managed-file-drift.sh check <project-dir>
#       Prints one "<path>: outdated" or "<path>: missing" line per managed file
#       whose content differs from the shipped template, or that is absent.
#       An "outdated" path accepted in <project-dir>/.claude/managed-file-drift.accept
#       (see below) is not reported. Exit 0 = clean, 1 = drift found.
#   managed-file-drift.sh accept <project-dir> <path>
#       Prints the accept-file line for the current contents of an outdated
#       managed path. It never writes the accept file; append the line yourself.
#   managed-file-drift.sh list
#       Prints the managed paths, one per line, in the Upgrade U2 order.
#   Exit 2 = usage error, unreadable project directory or template tree,
#   malformed accept-file line, or an accept path that is unmanaged or not outdated.
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
#   hooks     — every plugin hooks/*-guard.sh and task-validator.sh must
#               match .claude/hooks/<name>.sh, except the plugin-only guards
#               in PLUGIN_ONLY, which never had a project copy.
#   allow     — JSON equal to the template once permissions.allow is set
#               aside, and that array holds every template rule; added rules
#               (the pptx helpers Upgrade U4 merges in) are not drift. Without
#               jq on PATH the rule falls back to exact.
#   runargs   — byte-identical to merge-runargs.sh's output for the file: the
#               template with the file's own extra "runArgs" elements kept.
#
# Gates skip a row silently: "devcontainer" without a .devcontainer/ directory,
# "git" without a .git/ directory.
#
# Plugin hooks (design/plugin-delivered-project-files-prd.md US-006) change two
# things. In a project whose .claude/ralph.json sets "pluginHooks": true (read
# with jq; without jq the project counts as not migrated), the plugin owns the
# six managed Claude guards and the common allow rules: .claude/settings.local.json
# and the guard copies are no longer compared, and a
# copy of a guard the marker does not list in "localGuards" is reported as
# "<path>: legacy copy" (migrate-plugin-hooks.sh tracked deletes it). When the
# clone is shimmed too (below), a missing .claude/hooks/filename-length-guard.sh
# is not reported either (tracked --retire-legacy deletes it); a present copy is
# still compared. In a clone
# whose git config ralph.pluginHooks is true, the three git hooks are compared
# with the plugin shim (templates/shims/git-hook) instead of the legacy bodies.
# .claude/settings.json, .devcontainer/Dockerfile (assembled) and .gitignore
# (append-only) are never compared: ralph-init no longer ships a settings.json,
# and migrate-plugin-hooks.sh tracked removes the legacy guard entries from it.
# Project-owned files — .claude/task-reviewer-rules.md above all — are not in
# the table and are never read.
#
# The accept file records reviewed, deliberate differences, one line per path:
#
#   <path> template=<sha256> project=<sha256>
#
# Blank lines and "#" comments are allowed. Each hash covers exactly the bytes
# the path's rule compares — the whole file, except the lines above <h> for
# above:<h> — so the acceptance lapses, and the path is reported again, as soon
# as either side changes. A missing path is always reported.
set -euo pipefail

usage() {
  echo "usage: managed-file-drift.sh check <project-dir> | accept <project-dir> <path> | list" >&2
  exit 2
}

# path|template (plugin-root-relative)|rule|gate
table() {
  cat <<'ROWS'
ralph.sh|skills/ralph-init/templates/root/ralph.sh|exact|-
refine.sh|skills/ralph-init/templates/root/refine.sh|exact|-
CLAUDE.md|skills/ralph-init/templates/root/CLAUDE.md|above:## Project-Specific|-
.git/hooks/post-commit|git-hooks/post-commit|exact|git
.git/hooks/commit-msg|git-hooks/commit-msg|exact|git
.git/hooks/pre-commit|git-hooks/pre-commit|exact|git
.claude/hooks/|hooks/|hooks|-
.claude/settings.local.json|skills/ralph-init/templates/claude/settings.local.json|allow|-
.devcontainer/devcontainer.json|skills/ralph-init/templates/devcontainer/devcontainer.json|runargs|devcontainer
.devcontainer/init-firewall.sh|skills/ralph-init/templates/devcontainer/init-firewall.sh|exact|devcontainer
.claude/brainstorm-rules.md|skills/ralph-init/templates/claude/brainstorm-rules.md|above:## Project additions|-
.devcontainer/container-settings.local.json|skills/ralph-init/templates/devcontainer/container-settings.local.json|exact|devcontainer
ROWS
}

# Print the lines of $2 above the first line equal to $1.
above() {
  awk -v h="$1" '$0 == h { exit } { print }' "$2"
}

# Succeed when settings file $1 matches template $2 under the allow rule.
allow_current() {
  command -v jq >/dev/null 2>&1 || { cmp -s "$1" "$2"; return; }
  jq -en --slurpfile p "$1" --slurpfile t "$2" '
    ($p[0] | del(.permissions.allow)) == ($t[0] | del(.permissions.allow))
    and (($t[0].permissions.allow // []) - ($p[0].permissions.allow // []) == [])
  ' >/dev/null 2>&1
}

# Print "missing" or "outdated" when project file $1 differs from template $2
# under rule $3; print nothing when it is current.
state() {
  local path=$1 tmpl=$2 rule=$3 file=$project/$1
  [ -r "$tmpl" ] || { echo "managed-file-drift: cannot read $tmpl" >&2; exit 2; }
  if [ ! -e "$file" ]; then
    echo missing
  elif [ "$rule" = exact ]; then
    cmp -s "$file" "$tmpl" || echo outdated
  elif [ "$rule" = allow ]; then
    allow_current "$file" "$tmpl" || echo outdated
  elif [ "$rule" = runargs ]; then
    cmp -s "$file" <(bash "$here/merge-runargs.sh" "$tmpl" "$file") || echo outdated
  else
    local heading=${rule#above:}
    if ! grep -Fxq -- "$heading" "$file" || ! cmp -s <(above "$heading" "$file") <(above "$heading" "$tmpl"); then
      echo outdated
    fi
  fi
}

# SHA-256 of stdin, hex only: shasum on macOS, sha256sum on GNU systems.
sha256() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | cut -d' ' -f1
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum | cut -d' ' -f1
  else
    echo "managed-file-drift: neither shasum nor sha256sum is on PATH" >&2
    exit 2
  fi
}

# Hash the bytes of file $1 that rule $2 compares.
digest() {
  case $2 in
    (above:*) above "${2#above:}" "$1" | sha256 ;;
    (*) sha256 <"$1" ;;
  esac
}

# Print the accept-file line for project path $1, template $2 and rule $3.
accept_line() {
  local t p
  t=$(digest "$2" "$3") || exit 2
  p=$(digest "$project/$1" "$3") || exit 2
  echo "$1 template=$t project=$p"
}

# Print a drift line for project path $1 unless it is current or accepted.
compare() {
  local s line
  s=$(state "$@") || exit 2
  [ -n "$s" ] || return 0
  if [ "$s" = outdated ] && [ -n "$accepted" ]; then
    line=$(accept_line "$@") || exit 2
    printf '%s\n' "$accepted" | grep -Fxq -- "$line" && return 0
  fi
  echo "$1: $s"
}

# Print the accept file's entries; exit 2 naming the first malformed line.
load_accepted() {
  local file=$project/.claude/managed-file-drift.accept line n=0
  [ -e "$file" ] || return 0
  [ -r "$file" ] || { echo "managed-file-drift: cannot read $file" >&2; exit 2; }
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    case $line in (*[![:space:]]*) ;; (*) continue ;; esac
    case ${line#"${line%%[![:space:]]*}"} in ('#'*) continue ;; esac
    if ! printf '%s\n' "$line" | grep -Eq '^[^[:space:]]+ template=[0-9a-f]{64} project=[0-9a-f]{64}$'; then
      echo "managed-file-drift: $file:$n: malformed line, want '<path> template=<sha256> project=<sha256>'" >&2
      exit 2
    fi
    printf '%s\n' "$line"
  done <"$file"
}

# Print "<template>|<rule>" for managed project path $1; fail when unmanaged.
lookup() {
  local path tmpl rule gate hook
  while IFS='|' read -r path tmpl rule gate; do
    if [ "$rule" = hooks ]; then
      for hook in "$root/$tmpl"*-guard.sh "$root/${tmpl}task-validator.sh"; do
        plugin_only "$hook" && continue
        [ "$1" = "$path${hook##*/}" ] && { echo "$hook|exact"; return 0; }
      done
    elif [ "$1" = "$path" ]; then
      echo "$root/$tmpl|$rule"
      return 0
    fi
  done < <(table)
  return 1
}

GUARDS="commit-msg-guard commit-prefix-guard master-branch-guard naming-guard notes-guard task-validator"
# Guards hooks.json calls directly, outside the marker gate; no project copies them.
PLUGIN_ONLY="autonomous-create-guard"

# Succeed when plugin hook script $1 is one of PLUGIN_ONLY.
plugin_only() {
  local name=${1##*/}
  case " $PLUGIN_ONLY " in (*" ${name%.sh} "*) return 0 ;; esac
  return 1
}

# Set migrated, locals and shimmed for the project (see the header).
plugin_state() {
  local marker=$project/.claude/ralph.json
  migrated=0 locals="" shimmed=0
  if [ -f "$marker" ] && command -v jq >/dev/null 2>&1 && jq -e '.pluginHooks == true' "$marker" >/dev/null 2>&1; then
    migrated=1
    locals=$(jq -r '.localGuards // [] | .[]? | strings' "$marker" 2>/dev/null || true)
  fi
  if [ -d "$project/.git" ] && [ "$(git -C "$project" config --bool ralph.pluginHooks 2>/dev/null || true)" = true ]; then
    shimmed=1
  fi
}

# Print the state the plugin gives managed path $1: "skip" when a migrated
# project no longer manages it, "legacy" for a leftover legacy guard copy,
# nothing when the table's rule applies.
plugin_owned() {
  local name
  [ "$migrated" -eq 1 ] || return 0
  case $1 in
    (.claude/settings.local.json) echo skip; return 0 ;;
    (.claude/hooks/*.sh) name=${1#.claude/hooks/} name=${name%.sh} ;;
    (*) return 0 ;;
  esac
  if [ "$name" = filename-length-guard ]; then
    # tracked --retire-legacy deletes it once this clone runs the shim.
    [ "$shimmed" -eq 0 ] || [ -e "$project/$1" ] || echo skip
    return 0
  fi
  case " $GUARDS " in (*" $name "*) ;; (*) return 0 ;; esac
  if printf '%s\n' "$locals" | grep -Fxq -- "$name" || [ ! -e "$project/$1" ]; then
    echo skip
  else
    echo legacy
  fi
}

# Print the template managed path $1 is compared with: the plugin shim for a
# git hook in a shimmed clone, else $2.
template_for() {
  case $shimmed:$1 in
    (1:.git/hooks/pre-commit | 1:.git/hooks/commit-msg | 1:.git/hooks/post-commit)
      echo "$root/skills/ralph-init/templates/shims/git-hook" ;;
    (*) echo "$2" ;;
  esac
}

[ $# -ge 1 ] || usage
case $1 in
  list)
    [ $# -eq 1 ] || usage
    table | cut -d'|' -f1
    exit 0
    ;;
  check) [ $# -eq 2 ] || usage ;;
  accept) [ $# -eq 3 ] || usage ;;
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

plugin_state
if [ "$1" = accept ]; then
  found=$(lookup "$3") || { echo "managed-file-drift: $3 is not a managed path" >&2; exit 2; }
  [ -z "$(plugin_owned "$3")" ] || {
    echo "managed-file-drift: $3 is not managed in a project migrated to plugin hooks" >&2
    exit 2
  }
  tmpl=$(template_for "$3" "${found%|*}") rule=${found##*|}
  s=$(state "$3" "$tmpl" "$rule") || exit 2
  case $s in
    (outdated) accept_line "$3" "$tmpl" "$rule" ;;
    (missing) echo "managed-file-drift: $3 is missing; only an outdated file can be accepted" >&2; exit 2 ;;
    (*) echo "managed-file-drift: $3 matches the template; there is nothing to accept" >&2; exit 2 ;;
  esac
  exit 0
fi

accepted=$(load_accepted) || exit 2
report=$(
  table | while IFS='|' read -r path tmpl rule gate; do
    case $gate in
      (git) [ -d "$project/.git" ] || continue ;;
      (devcontainer) [ -d "$project/.devcontainer" ] || continue ;;
    esac
    if [ "$rule" = hooks ]; then
      for hook in "$root/$tmpl"*-guard.sh "$root/${tmpl}task-validator.sh"; do
        plugin_only "$hook" && continue
        case $(plugin_owned "$path${hook##*/}") in
          (skip) ;;
          (legacy) echo "$path${hook##*/}: legacy copy" ;;
          (*) compare "$path${hook##*/}" "$hook" exact ;;
        esac
      done
    else
      [ -z "$(plugin_owned "$path")" ] || continue
      compare "$path" "$(template_for "$path" "$root/$tmpl")" "$rule"
    fi
  done
)
[ -n "$report" ] || exit 0
printf '%s\n' "$report"
exit 1
