#!/usr/bin/env bash
# master-provenance.sh — check where each commit on master came from, for the
# task-reviewer's R-INFRA-6. It walks the first-parent commits of a range of
# master and prints one line per commit: "ok <sha> <reason>" or
# "FLAG <sha> <reason>". It changes nothing.
#
# Usage: master-provenance.sh [--remote NAME] [--base BRANCH] [RANGE]
#
#   RANGE      the commits to check (default REMOTE/BASE..BASE, the commits
#              master has that origin lacks, or all of BASE when there is no
#              REMOTE/BASE); task notes are read at its end
#   --remote   the remote integrate merges from (default origin)
#   --base     the base branch (default master)
#
# Allowed on master:
#   - a commit that changes only master-branch-guard allowlist paths (.claude/,
#     design/, .obsidian/, .vscode/, .idea/, .cursor/, .zed/, .fleet/,
#     .gitignore files);
#   - a "task-N: " commit that changes only backlog/{tasks,drafts,archive,completed}/;
#   - task-branch work: a merge whose second parent is at or after a
#     "Review: APPROVED <sha>" recorded in the notes of the task it names, or a
#     fast-forwarded "task-N" commit at or before such a SHA on master's
#     first-parent line. Only bookkeeping
#     commits may follow the SHA: task-N commits that change task files, guard
#     allowlist paths or the project's master_bookkeeping_paths;
#   - an integration merge whose "Integrated-Origin: <sha>" trailer names its
#     second parent, a SHA reachable from REMOTE/BASE.
# A merge must also have the tree `git merge-tree --write-tree` makes of its
# parents, unless some task's notes record "Integration review: APPROVED
# <merge-sha>" for exactly that merge.
#
# .claude/task-reviewer.conf may set (the last line of each wins):
#   master_bookkeeping_paths=  a space-separated list of extra path prefixes,
#                              for files a project's lifecycle changes after
#                              the review, such as a version bump;
#   master_provenance_since=   a commit; the default range leaves out it and
#                              its ancestors, the history from before a
#                              project recorded Review: APPROVED notes.
#
# Exit status: 0 when every commit is allowed, 1 when one is flagged, 2 on a
# usage or git error. Needs git 2.38 or later (merge-tree --write-tree).

set -u

REMOTE=origin
BASE=master
RANGE=''
FLAGS=0
EXTRA_PATHS=''
TIP=''
TASK_FILES=''
FIRST_PARENTS=''

die() { printf 'master-provenance: %s\n' "$*" >&2; exit 2; }

usage() { sed -n '2,/^$/s/^# \{0,1\}//p' "$0" >&2; exit 2; }

ok() { printf 'ok %s %s\n' "$(git rev-parse --short "$1")" "$2"; }

flag() { printf 'FLAG %s %s\n' "$(git rev-parse --short "$1")" "$2"; FLAGS=1; }

# guard_path PATH — 0 when the master-branch guard lets an edit to PATH through.
guard_path() {
  case "$1" in
    .claude/*|*/.claude/*|design/*|*/design/*|.obsidian/*|*/.obsidian/*) return 0 ;;
    .vscode/*|*/.vscode/*|.idea/*|*/.idea/*|.cursor/*|*/.cursor/*) return 0 ;;
    .zed/*|*/.zed/*|.fleet/*|*/.fleet/*|.gitignore|*/.gitignore) return 0 ;;
  esac
  return 1
}

task_path() {
  case "$1" in
    backlog/tasks/*|backlog/drafts/*|backlog/archive/*|backlog/completed/*) return 0 ;;
  esac
  return 1
}

extra_path() {
  local p
  for p in $EXTRA_PATHS; do
    case "$1" in "$p"|"$p"/*|"${p%/}"/*) return 0 ;; esac
  done
  return 1
}

# all_paths COMMIT TEST... — 0 when every path COMMIT changes passes one TEST.
all_paths() {
  local c=$1 path t
  shift
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    for t in "$@"; do "$t" "$path" && continue 2; done
    return 1
  done <<EOF
$(git diff-tree --no-commit-id --name-only -r --root "$c")
EOF
  return 0
}

# parent_count COMMIT — the number of words in "COMMIT PARENT...".
parent_count() { git rev-list --parents -n 1 "$1" | awk '{ print NF }'; }

# subject_task COMMIT — the N of the first "task-N" in COMMIT's subject.
subject_task() {
  git log -1 --format=%s "$1" | grep -oE '[Tt][Aa][Ss][Kk]-[0-9]+' | head -n 1 | sed 's/.*-//'
}

direct_task_commit() {
  git log -1 --format=%s "$1" | grep -q '^task-[0-9][0-9]*: ' && all_paths "$1" task_path
}

bookkeeping() {
  [ "$(parent_count "$1")" -le 2 ] || return 1
  git log -1 --format=%s "$1" | grep -q '^task-[0-9][0-9]*: ' || all_paths "$1" guard_path || return 1
  all_paths "$1" task_path guard_path extra_path
}

# task_notes N — the task files of TASK-N at the end of the range.
task_notes() {
  local f
  printf '%s\n' "$TASK_FILES" | while IFS= read -r f; do
    case "${f##*/}" in
      "task-$1 "*|"task-$1.md") git show "$TIP:$f" ;;
    esac
  done
}

# approved N — the full SHAs of TASK-N's "Review: APPROVED <sha>" notes.
approved() {
  local s
  task_notes "$1" | grep -oE 'Review: APPROVED [0-9a-f]{7,40}' | sed 's/.* //' |
    while IFS= read -r s; do git rev-parse -q --verify "$s^{commit}" 2>/dev/null; done
}

# reviewed_after A TIP EXCLUDE — 0 when A is TIP or an ancestor of it and every
# commit of A..TIP not in EXCLUDE is a bookkeeping commit.
reviewed_after() {
  local c
  git merge-base --is-ancestor "$1" "$2" || return 1
  for c in $(git rev-list "$1..$2" ${3:+"^$3"}); do bookkeeping "$c" || return 1; done
  return 0
}

integration_reviewed() {
  local m s
  m=$(git rev-parse "$1")
  for s in $(printf '%s\n' "$TASK_FILES" | while IFS= read -r f; do git show "$TIP:$f"; done |
    grep -oE 'Integration review: APPROVED [0-9a-f]{7,40}' | sed 's/.* //'); do
    [ "$(git rev-parse -q --verify "$s^{commit}" 2>/dev/null)" = "$m" ] && return 0
  done
  return 1
}

# check_tree MERGE REASON — ok when MERGE's tree is git's own merge of its
# parents or an integration review approves it.
check_tree() {
  local tree
  tree=$(git merge-tree --write-tree "$1^1" "$1^2" 2>/dev/null | head -n 1)
  if [ "$tree" = "$(git rev-parse "$1^{tree}")" ]; then ok "$1" "$2"
  elif integration_reviewed "$1"; then ok "$1" "$2, hand-resolved with an integration review"
  else flag "$1" "$2, but its tree differs from git merge-tree of its parents and no Integration review: APPROVED names it"
  fi
}

check_merge() {
  local m=$1 p2 trailer n a
  p2=$(git rev-parse "$m^2")
  trailer=$(git log -1 --format=%B "$m" | sed -n 's/^Integrated-Origin: *\([0-9a-f]\{7,40\}\) *$/\1/p' | tail -n 1)
  if [ -n "$trailer" ]; then
    if [ "$(git rev-parse -q --verify "$trailer^{commit}" 2>/dev/null)" != "$p2" ]; then
      flag "$m" "Integrated-Origin trailer does not name the second parent"
    elif ! git rev-parse -q --verify "refs/remotes/$REMOTE/$BASE" >/dev/null; then
      flag "$m" "integration merge, but $REMOTE/$BASE is unknown"
    elif ! git merge-base --is-ancestor "$p2" "refs/remotes/$REMOTE/$BASE"; then
      flag "$m" "Integrated-Origin $(git rev-parse --short "$p2") is not reachable from $REMOTE/$BASE"
    else check_tree "$m" "integration merge of $REMOTE/$BASE"
    fi
    return
  fi
  n=$(subject_task "$m")
  [ -n "$n" ] || { flag "$m" "merge names no task and has no Integrated-Origin trailer"; return; }
  for a in $(approved "$n"); do
    if reviewed_after "$a" "$p2" "$m^1"; then
      check_tree "$m" "merge of TASK-$n reviewed at $(git rev-parse --short "$a")"
      return
    fi
  done
  flag "$m" "merge of TASK-$n: no Review: APPROVED note of TASK-$n names its second parent or a commit it follows with bookkeeping only"
}

check_commit() {
  local c=$1 n a
  if all_paths "$c" guard_path; then ok "$c" "master-branch guard allowlist paths only"; return; fi
  if direct_task_commit "$c"; then ok "$c" "task-file commit"; return; fi
  n=$(git log -1 --format=%s "$c" | sed -n 's/^task-\([0-9][0-9]*\)[^0-9].*/\1/p')
  if [ -n "$n" ]; then
    for a in $(approved "$n"); do
      # The reviewed tip must itself be on master's first-parent line: a
      # task-N commit behind a SHA that came in as a merge's second parent
      # is a commit made on master before the branch forked.
      printf '%s\n' "$FIRST_PARENTS" | grep -qx "$a" || continue
      if git merge-base --is-ancestor "$c" "$a" || reviewed_after "$a" "$c" ''; then
        ok "$c" "fast-forwarded TASK-$n work reviewed at $(git rev-parse --short "$a")"
        return
      fi
    done
  fi
  flag "$c" "direct commit outside the guard allowlist and task files, not covered by a Review: APPROVED note"
}

# conf_value KEY — the last value of KEY in .claude/task-reviewer.conf.
conf_value() {
  local conf
  conf="$(git rev-parse --show-toplevel)/.claude/task-reviewer.conf"
  [ -f "$conf" ] || return 0
  sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$conf" | tail -n 1 | sed 's/[[:space:]]*$//'
}

main() {
  local c parents since
  while [ $# -gt 0 ]; do
    case "$1" in
      --remote) [ $# -ge 2 ] || usage; REMOTE=$2; shift 2 ;;
      --base) [ $# -ge 2 ] || usage; BASE=$2; shift 2 ;;
      -h|--help) usage ;;
      -*) usage ;;
      *) [ -z "$RANGE" ] || usage; RANGE=$1; shift ;;
    esac
  done
  git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository"
  since=''
  if [ -z "$RANGE" ]; then
    RANGE="refs/remotes/$REMOTE/$BASE..$BASE"
    if ! git rev-parse -q --verify "refs/remotes/$REMOTE/$BASE" >/dev/null; then
      printf 'master-provenance: no %s/%s; checking all of %s\n' "$REMOTE" "$BASE" "$BASE" >&2
      RANGE=$BASE
    fi
    since=$(conf_value master_provenance_since)
    if [ -n "$since" ]; then
      since=$(git rev-parse -q --verify "$since^{commit}") || die "cannot resolve master_provenance_since"
    fi
  fi
  TIP=${RANGE##*..}
  TIP=$(git rev-parse -q --verify "${TIP:-HEAD}^{commit}") || die "cannot resolve the end of $RANGE"
  git rev-list -n 1 "$RANGE" >/dev/null 2>&1 || die "cannot resolve range $RANGE"
  git merge-tree --write-tree "$TIP" "$TIP" >/dev/null 2>&1 || die "git merge-tree --write-tree failed (needs git 2.38+)"
  TASK_FILES=$(git -c core.quotePath=false ls-tree -r --name-only "$TIP" -- backlog/tasks backlog/completed backlog/archive backlog/drafts)
  EXTRA_PATHS=$(conf_value master_bookkeeping_paths)
  FIRST_PARENTS=$(git rev-list --first-parent "$TIP")
  for c in $(git rev-list --first-parent --reverse "$RANGE" ${since:+"^$since"}); do
    parents=$(parent_count "$c")
    if [ "$parents" -gt 3 ]; then flag "$c" "octopus merge"
    elif [ "$parents" -eq 3 ]; then check_merge "$c"
    else check_commit "$c"
    fi
  done
  return "$FLAGS"
}

main "$@"
