#!/usr/bin/env bash
# handoff-create.sh — create a /ralph-handoff task in a destination Ralph project
# the way the destination's shared-backlog state asks for
# (design/plugin-delivered-project-files-prd.md US-023). Two inputs decide: the
# destination's marker, "sharedBacklog" in .claude/ralph.json at its work tree
# root, and its clone switch, git config ralph.sharedBacklog.
#
#   marker  switch        mode      behaviour
#   true    true          protocol  the plugin's shared-backlog.sh create; the
#                                   ID is final once create returns 0
#   true    unset/false   refuse    exit 1, naming the enable step
#   other   true          protocol  the switch is trusted
#   other   unset/false   local     backlog task create; the file stays
#                                   uncommitted and its ID is provisional
#
# Usage: handoff-create.sh mode DEST
#          print the mode (protocol, refuse or local); refuse also exits 1
#        handoff-create.sh create DEST <backlog task create args...>
#          create the task and print, on stdout:
#            mode: protocol|local
#            id: TASK-<n>
#            state: final|provisional
#            path: <task file, relative to DEST's root>
#
# protocol mode never touches DEST's branch, index or working tree (create works
# in a temporary worktree at origin/master), so a destination behind origin,
# ahead of it, dirty or on a task branch is fine; the task reaches DEST's work
# tree on its next `scripts/shared-backlog.sh sync`. Nothing is printed on
# stdout until create has returned 0.
#
# Exit codes: 0 created (or mode printed), 1 refused or failed, 2 origin
# unreachable (from create), 64 usage error. Bash 3.2 clean.

set -eu
unset CDPATH

SELF_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SB="$SELF_DIR/../../../scripts/shared-backlog.sh"

die() { say "$*"; exit 1; }
say() { echo "ralph-handoff: $*" >&2; }
usage() { awk '/^# Usage:/ { p = 1 } p && /^#$/ { exit } p { sub(/^# ?/, ""); print }' "$SELF_DIR/$(basename "$0")" >&2; exit 64; }

# dest_root DEST — the work tree root of DEST.
dest_root() {
  git -C "$1" rev-parse --show-toplevel 2>/dev/null || die "$1 is not inside a git work tree"
}

# marker_on ROOT — 0 when ROOT/.claude/ralph.json sets "sharedBacklog": true.
marker_on() {
  local jq
  [ -f "$1/.claude/ralph.json" ] || return 1
  jq=$(command -v jq 2>/dev/null) || jq=$(git -C "$1" config --get ralph.jq 2>/dev/null) || jq=''
  [ -n "$jq" ] && [ -x "$jq" ] ||
    die "jq not found (PATH or git config ralph.jq); cannot read $1/.claude/ralph.json"
  "$jq" -e '.sharedBacklog == true' "$1/.claude/ralph.json" >/dev/null 2>&1
}

# switch_on ROOT — 0 when ROOT's clone has git config ralph.sharedBacklog true.
switch_on() {
  [ "$(git -C "$1" config --bool --get ralph.sharedBacklog 2>/dev/null || true)" = true ]
}

# mode_of ROOT — print protocol, refuse or local.
mode_of() {
  if switch_on "$1"; then
    echo protocol
  elif marker_on "$1"; then
    echo refuse
  else
    echo local
  fi
}

refuse() {
  die "$1 opts in to the shared-backlog protocol (.claude/ralph.json sets \"sharedBacklog\": true) but this clone has not enabled it (git config ralph.sharedBacklog is not true); run \`cd $1 && scripts/shared-backlog.sh enable\` there first, then hand off again; nothing created"
}

create_protocol() {
  local root=$1 out rc=0 id path
  shift
  [ -f "$SB" ] || die "the plugin's shared-backlog script $SB is missing"
  out=$(cd "$root" && bash "$SB" create "$@") || rc=$?
  if [ "$rc" -ne 0 ]; then
    [ -z "$out" ] || printf '%s\n' "$out" >&2
    say "shared-backlog.sh create exited $rc; no task ID to report"
    exit "$rc"
  fi
  id=$(printf '%s\n' "$out" | sed -n 's/^created TASK-\([0-9.]*\) [0-9a-f]* \(.*\) (Shared-Backlog-Op: .*/\1/p' | head -1)
  path=$(printf '%s\n' "$out" | sed -n 's/^created TASK-[0-9.]* [0-9a-f]* \(.*\) (Shared-Backlog-Op: .*/\1/p' | head -1)
  [ -n "$id" ] || die "create returned 0 but its report has no task ID: $out"
  printf 'mode: protocol\nid: TASK-%s\nstate: final\npath: %s\n' "$id" "$path"
}

create_local() {
  local root=$1 out id file
  shift
  out=$(cd "$root" && backlog task create "$@" --plain) || die "backlog task create failed: $out"
  id=$(printf '%s\n' "$out" | sed -n 's/^Task [A-Za-z]*-\([0-9.]*\) - .*/\1/p' | head -1)
  file=$(printf '%s\n' "$out" | sed -n 's/^File: //p' | head -1)
  [ -n "$id" ] || die "cannot read the new task ID from: $out"
  printf 'mode: local\nid: TASK-%s\nstate: provisional\npath: %s\n' "$id" "${file#"$root"/}"
}

[ $# -ge 2 ] || usage
cmd=$1
root=$(dest_root "$2") || exit 1
shift 2
case "$cmd" in mode | create) ;; *) usage ;; esac
mode=$(mode_of "$root") || exit 1
case "$cmd" in
  mode)
    [ $# -eq 0 ] || usage
    echo "$mode"
    [ "$mode" != refuse ] || exit 1
    ;;
  create)
    [ $# -gt 0 ] || usage
    case "$mode" in
      protocol) create_protocol "$root" "$@" ;;
      refuse) refuse "$root" ;;
      *) create_local "$root" "$@" ;;
    esac
    ;;
esac
