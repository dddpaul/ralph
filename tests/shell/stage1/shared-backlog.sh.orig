#!/usr/bin/env bash
# shared-backlog.sh — claim tasks, allocate task IDs and integrate finished work
# when several hosts share one origin. The push to origin decides: the server
# accepts only fast-forward pushes, so of two competing claims or task IDs only
# one lands, and the loser finds out on its next pull. See the "Shared repo
# protocol" section of CLAUDE.md for when each subcommand runs, and
# design/multi-host-parallel-work-brainstorm.md for the reasoning.
#
# Usage: scripts/shared-backlog.sh <command> [args]
#
#   sync                 bounded `git pull --ff-only origin master`
#   claim N [--as @who] [--force]
#                        assign TASK-N to the holder and push the claim
#   release N [--as @who] [--force]
#                        clear the holder's assignee on TASK-N and push
#   create <backlog task create args...>
#                        sync, create a task, commit and push it at once
#   integrate [--task N] land local master on origin: merge origin/master,
#                        renumber our duplicate IDs, rerun checks, push
#   check-dupes [REV]    exit 1 if REV's tree (default HEAD) has duplicate IDs
#   renumber [--base REF]
#                        renumber our copies of duplicate IDs (those not in REF,
#                        default origin/master) and commit
#   install-hooks [--force]
#                        install scripts/hooks/pre-push into .git/hooks
#
# The holder defaults to $SHARED_BACKLOG_HOLDER. $SHARED_BACKLOG_CHECKS, when
# set, replaces the checks integrate reruns (run with `sh -c` at the repo root).
#
# Exit codes: 0 ok, 1 refused / conflict / check failed, 2 origin unreachable,
# 64 usage error. Bash 3.2 clean: no associative arrays, no mapfile.

set -eu

REMOTE=origin
BRANCH=master
MAX_TRIES=3
HOOK_MARKER='shared-backlog pre-push hook'

die() { echo "shared-backlog: $*" >&2; exit 1; }
usage() { sed -n '/^# Usage:/,/^# Exit codes/p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 64; }
say() { echo "shared-backlog: $*" >&2; }

# Every network call is bounded and never prompts: BatchMode refuses SSH
# passphrase/password prompts, ConnectTimeout caps a dead host at 5 s, and the
# http.lowSpeed pair aborts a stalled HTTPS transfer after 10 s.
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${SHARED_BACKLOG_SSH:-ssh -o BatchMode=yes -o ConnectTimeout=5}"
net_git() { git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=10 "$@"; }

repo_root() { git rev-parse --show-toplevel; }

task_prefix() {
  local p
  p=$(sed -n 's/^task_prefix: *["'\'']\{0,1\}\([^"'\'']*\)["'\'']\{0,1\} *$/\1/p' \
    backlog/config.yml 2>/dev/null | head -1)
  echo "${p:-task}"
}

# --- task files -------------------------------------------------------------

# task_file N — path of TASK-N's file in the working tree (active or completed).
task_file() {
  local pfx f
  pfx=$(task_prefix)
  for f in backlog/tasks/"$pfx-$1 - "*.md backlog/tasks/"$pfx-$1".md \
           backlog/completed/"$pfx-$1 - "*.md backlog/completed/"$pfx-$1".md; do
    [ -f "$f" ] && { echo "$f"; return 0; }
  done
  return 1
}

# fm_scalar FILE KEY — a scalar frontmatter value, quotes stripped.
fm_scalar() {
  awk -v key="$2" '
    NR == 1 && $0 == "---" { infm = 1; next }
    infm && $0 == "---" { exit }
    infm && index($0, key ":") == 1 {
      v = substr($0, length(key) + 2); sub(/^ +/, "", v); sub(/ +$/, "", v)
      gsub(/^["\047]|["\047]$/, "", v); print v; exit
    }' "$1"
}

# fm_list FILE KEY — a list frontmatter value, one item per line, either block
# style ("key:" then "  - item") or flow style ("key: [a, b]").
fm_list() {
  awk -v key="$2" '
    NR == 1 && $0 == "---" { infm = 1; next }
    infm && $0 == "---" { exit }
    !infm { next }
    inlist && /^ +- / { v = $0; sub(/^ +- +/, "", v); gsub(/^["\047]|["\047]$/, "", v); print v; next }
    inlist { exit }
    index($0, key ":") == 1 {
      v = substr($0, length(key) + 2); sub(/^ +/, "", v); sub(/ +$/, "", v)
      if (v == "") { inlist = 1; next }
      gsub(/^\[|\]$/, "", v); n = split(v, a, /, */)
      for (i = 1; i <= n; i++) { gsub(/^["\047 ]+|["\047 ]+$/, "", a[i]); if (a[i] != "") print a[i] }
      exit
    }' "$1"
}

# tree_task_ids REV — "ID<TAB>path" for every task file in REV's tree.
tree_task_ids() {
  local pfx
  pfx=$(task_prefix)
  git -c core.quotePath=false ls-tree -r --name-only "$1" -- \
      backlog/tasks backlog/completed backlog/archive/tasks 2>/dev/null |
    awk -v pfx="$pfx" '{
      n = split($0, parts, "/"); b = parts[n]
      if (index(b, pfx "-") != 1) next
      id = substr(b, length(pfx) + 2)
      if (match(id, /^[0-9]+(\.[0-9]+)*/) == 0) next
      print substr(id, 1, RLENGTH) "\t" $0
    }'
}

# --- git helpers ------------------------------------------------------------

require_master_clean() {
  local b
  b=$(git symbolic-ref --short -q HEAD || true)
  [ "$b" = "$BRANCH" ] || die "must be on $BRANCH (on '${b:-detached HEAD}')"
  [ -z "$(git status --porcelain --untracked-files=no)" ] ||
    die "working tree has uncommitted changes; commit or stash them first"
}

# fetch_bounded — 0 on success, 2 when origin cannot be reached.
fetch_bounded() {
  net_git fetch -q "$REMOTE" "$BRANCH" 2>/dev/null && return 0
  say "origin unreachable ($(git remote get-url "$REMOTE" 2>/dev/null))"
  return 2
}

# push_master — 0 pushed, 1 refused (not a fast-forward), 2 unreachable,
# 3 rejected for another reason (the pre-push hook, a server hook).
push_master() {
  local err rc=0
  err=$(net_git push -q "$REMOTE" "HEAD:refs/heads/$BRANCH" 2>&1) || rc=$?
  [ "$rc" -eq 0 ] && return 0
  printf '%s\n' "$err" >&2
  case "$err" in
    # The last two are a push that lost a race inside the server.
    *'[rejected]'*|*non-fast-forward*|*'fetch first'*|*'failed to update ref'*|*'cannot lock ref'*) return 1 ;;
    *'Could not read from remote'*|*'unable to access'*|*'Could not resolve'*) return 2 ;;
  esac
  return 3
}

# --- sync -------------------------------------------------------------------

cmd_sync() {
  require_master_clean
  fetch_bounded || return 2
  git merge -q --ff-only "$REMOTE/$BRANCH" 2>/dev/null ||
    die "local $BRANCH has diverged from $REMOTE/$BRANCH; run integrate first"
  say "synced to $(git rev-parse --short HEAD)"
}

# require_level — local master carries nothing origin lacks. claim, release
# and create land with a rebase and undo with a reset; with unpushed work (an
# un-integrated Ralph run, a provisional task) on master, the rebase would
# flatten its merges and push it unchecked, and the reset would drop it.
require_level() {
  [ "$(git rev-parse HEAD)" = "$(git rev-parse "$REMOTE/$BRANCH")" ] ||
    die "local $BRANCH is ahead of $REMOTE/$BRANCH; run integrate first"
}

# --- duplicate IDs ----------------------------------------------------------

# dup_ids REV — the IDs that more than one task file in REV's tree carries.
dup_ids() { tree_task_ids "$1" | cut -f1 | sort | uniq -d; }

cmd_check_dupes() {
  local rev=${1:-HEAD} dups tmp rc=0
  git rev-parse -q --verify "$rev^{tree}" >/dev/null || die "unknown revision: $rev"
  dups=$(dup_ids "$rev")
  if [ -n "$dups" ]; then
    say "duplicate task IDs in $rev:"
    for id in $dups; do
      tree_task_ids "$rev" | awk -F'\t' -v id="$id" '$1 == id { print "  " $2 }' >&2
    done
    rc=1
  fi
  # backlog doctor also sees documents, decisions and drafts, and dependency
  # cycles; run it on an export of exactly this tree, not the working tree.
  if command -v backlog >/dev/null 2>&1; then
    tmp=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog.XXXXXX")
    git archive "$rev" backlog | tar -x -C "$tmp"
    if ! (cd "$tmp" && backlog doctor >"$tmp/.doctor.out" 2>&1); then
      sed 's/^/  doctor: /' "$tmp/.doctor.out" >&2
      rc=1
    fi
    rm -rf "$tmp"
  else
    say "backlog not on PATH; checked file names only"
  fi
  return "$rc"
}

# renumber_one PATH OLD NEW — rename the file and rewrite its frontmatter ID.
renumber_one() {
  local path=$1 old=$2 new=$3 pfx dir base newpath tmp
  pfx=$(task_prefix)
  dir=${path%/*}
  base=${path##*/}
  newpath="$dir/$pfx-$new${base#"$pfx-$old"}"
  git mv -- "$path" "$newpath" || return 1
  tmp="$newpath.tmp.$$"
  awk -v old="$old" -v new="$new" '
    NR == 1 && $0 == "---" { infm = 1; print; next }
    infm && $0 == "---" { infm = 0 }
    infm && /^id: / {
      v = substr($0, 5); q = ""
      if (v ~ /^["\047]/) { q = substr(v, 1, 1); v = substr(v, 2, length(v) - 2) }
      p = index(v, "-")
      if (substr(v, p + 1) == old) { print "id: " q substr(v, 1, p) new q; next }
    }
    { print }' "$newpath" >"$tmp" || return 1
  mv "$tmp" "$newpath" && git add -- "$newpath" || return 1
  echo "$newpath"
}

# cmd_renumber [--base REF] [--amend] — give our copies of duplicate IDs (the
# copies not in REF's tree) the next free IDs. Each renumber is its own commit;
# with --amend they are folded into HEAD instead, so that no commit carrying the
# duplicate ever reaches origin (create amends its own commit, integrate its
# merge commit).
cmd_renumber() {
  local base="$REMOTE/$BRANCH" amend='' dups id paths p keep next newpath n=0 log=''
  while [ $# -gt 0 ]; do
    case "$1" in
      --base) base=${2:?--base needs a ref}; shift 2 ;;
      --amend) amend=1; shift ;;
      *) usage ;;
    esac
  done
  git rev-parse -q --verify "$base^{tree}" >/dev/null || die "unknown base: $base"
  [ -z "$(git status --porcelain --untracked-files=no)" ] ||
    die "working tree has uncommitted changes; commit them first"
  dups=$(dup_ids HEAD)
  [ -n "$dups" ] || { say "no duplicate task IDs"; return 0; }
  next=$( (tree_task_ids HEAD; tree_task_ids "$base") | cut -f1 | cut -d. -f1 |
    sort -n | tail -1)
  for id in $dups; do
    case "$id" in *.*) die "TASK-$id is a subtask ID; renumber it by hand" ;; esac
    paths=$(tree_task_ids HEAD | awk -F'\t' -v id="$id" '$1 == id { print $2 }')
    # Theirs is the copy already on the base; ours are the rest. When no copy
    # is on the base (both unpushed), keep the first and renumber the others.
    keep=''
    while IFS= read -r p; do
      git cat-file -e "$base:$p" 2>/dev/null && { keep=$p; break; }
    done <<EOF
$paths
EOF
    [ -n "$keep" ] || keep=$(printf '%s\n' "$paths" | head -1)
    while IFS= read -r p; do
      [ "$p" = "$keep" ] && continue
      git cat-file -e "$base:$p" 2>/dev/null &&
        die "TASK-$id is duplicated on $base itself ($p); fix origin by hand"
      next=$((next + 1))
      newpath=$(renumber_one "$p" "$id" "$next") || die "renumbering $p failed"
      if [ -z "$amend" ]; then
        git commit -q -m "task-$next: renumber TASK-$id to TASK-$next" \
          -m "TASK-$id is taken on $base by $keep." || die "commit failed"
      fi
      log="${log}Renumbered TASK-$id to TASK-$next: TASK-$id is taken by $keep.
"
      echo "renumbered TASK-$id -> TASK-$next ($newpath)"
      n=$((n + 1))
    done <<EOF
$paths
EOF
  done
  if [ -n "$amend" ]; then
    git commit -q --amend -m "$(git log -1 --format=%B)" -m "$log" ||
      die "amending HEAD failed"
  fi
  say "renumbered $n task(s); check references to the old IDs in our unpushed work"
}

# --- linear landing (claim, release, create) --------------------------------

# land_linear VERIFY — push the commit(s) on top of origin/master; when the
# push is refused, rebase onto the new origin/master, call VERIFY (a function
# name; non-zero stops), and push again, at most MAX_TRIES times.
# Returns 0 pushed, 1 rebase conflict (aborted), 2 unreachable, 3 push
# rejected or refused MAX_TRIES times, 4 VERIFY failed.
land_linear() {
  local verify=$1 try=1 rc
  while :; do
    rc=0; push_master || rc=$?
    case "$rc" in
      0) return 0 ;;
      1) ;;
      *) return "$rc" ;;
    esac
    [ "$try" -ge "$MAX_TRIES" ] && { say "push refused $MAX_TRIES times"; return 3; }
    try=$((try + 1))
    fetch_bounded || return 2
    if ! git rebase -q "$REMOTE/$BRANCH" >/dev/null 2>&1; then
      git rebase --abort >/dev/null 2>&1 || true
      return 1
    fi
    "$verify" || return 4
  done
}

verify_none() { return 0; }

# --- claim / release --------------------------------------------------------

holder_from_args() {
  HOLDER=${SHARED_BACKLOG_HOLDER:-}
  FORCE=
  TASK_ID=
  while [ $# -gt 0 ]; do
    case "$1" in
      --as) HOLDER=${2:?--as needs @name}; shift 2 ;;
      --force) FORCE=1; shift ;;
      -*) usage ;;
      *) [ -z "$TASK_ID" ] || usage; TASK_ID=${1#*-}; shift ;;
    esac
  done
  [ -n "$TASK_ID" ] || usage
  [ -n "$HOLDER" ] || die "no holder: pass --as @name or set SHARED_BACKLOG_HOLDER"
  case "$HOLDER" in @*) ;; *) HOLDER="@$HOLDER" ;; esac
}

assignees() { local f; f=$(task_file "$1") || return 0; fm_list "$f" assignee; }

deps_done() {
  local f dep df st bad=
  f=$(task_file "$1")
  for dep in $(fm_list "$f" dependencies); do
    df=$(task_file "${dep#*-}") || { bad="$bad $dep(missing)"; continue; }
    st=$(fm_scalar "$df" status)
    [ "$st" = Done ] || bad="$bad $dep($st)"
  done
  [ -z "$bad" ] || { say "TASK-$1 has unfinished dependencies:$bad"; return 1; }
}

verify_claim() {
  local who
  who=$(assignees "$TASK_ID" | tr '\n' ' ')
  [ "$who" = "$HOLDER " ]
}

cmd_claim() {
  local f who st base rc=0
  holder_from_args "$@"
  cmd_sync || { rc=$?; [ "$rc" -eq 2 ] && say "cannot claim TASK-$TASK_ID: a claim nobody can see protects nothing"; return "$rc"; }
  require_level
  base=$(git rev-parse HEAD)
  f=$(task_file "$TASK_ID") || die "TASK-$TASK_ID not found"
  who=$(assignees "$TASK_ID" | tr '\n' ' ')
  who=${who% }
  if [ "$who" = "$HOLDER" ]; then say "TASK-$TASK_ID is already claimed by $HOLDER"; return 0; fi
  [ -z "$who" ] || die "TASK-$TASK_ID taken by $who"
  st=$(fm_scalar "$f" status)
  [ "$st" = "To Do" ] || die "TASK-$TASK_ID is '$st', not To Do"
  [ -n "$FORCE" ] || deps_done "$TASK_ID" || die "claim refused; --force overrides on Paul's say-so"
  backlog task edit "$TASK_ID" -a "$HOLDER" >/dev/null
  git add -- "$(task_file "$TASK_ID")"
  git commit -q -m "task-$TASK_ID: claim for $HOLDER"
  land_linear verify_claim || rc=$?
  [ "$rc" -eq 0 ] && { echo "claimed TASK-$TASK_ID $(git rev-parse --short HEAD)"; return 0; }
  # The claim did not land: drop it. Before the claim commit the tree was clean
  # and level with origin, so going back to that commit loses nothing; then
  # fast-forward to what origin has now.
  git reset -q --hard "$base"
  git merge -q --ff-only "$REMOTE/$BRANCH" 2>/dev/null || true
  case "$rc" in
    2) die "claim not pushed (origin unreachable); undone locally" ;;
    3) die "claim push rejected; undone locally" ;;
  esac
  # A conflict on the task file, or a clean rebase that leaves someone else's
  # name, means the other host claimed it first.
  who=$(assignees "$TASK_ID" | tr '\n' ' ')
  die "TASK-$TASK_ID taken by ${who% }"
}

cmd_release() {
  local f who rc=0
  holder_from_args "$@"
  cmd_sync || return $?
  require_level
  f=$(task_file "$TASK_ID") || die "TASK-$TASK_ID not found"
  who=$(assignees "$TASK_ID" | tr '\n' ' ')
  who=${who% }
  [ -n "$who" ] || { say "TASK-$TASK_ID has no assignee"; return 0; }
  [ "$who" = "$HOLDER" ] || [ -n "$FORCE" ] ||
    die "TASK-$TASK_ID is held by $who, not $HOLDER; --force overrides on Paul's say-so"
  backlog task edit "$TASK_ID" -a "" >/dev/null
  git add -- "$f"
  git commit -q -m "task-$TASK_ID: release from $who"
  land_linear verify_none || rc=$?
  case "$rc" in
    0) echo "released TASK-$TASK_ID $(git rev-parse --short HEAD)" ;;
    1) die "release conflicted with origin (rebase aborted; commit kept locally)" ;;
    2) die "release committed locally, not pushed (origin unreachable)" ;;
    *) die "release committed locally, not pushed" ;;
  esac
}

# --- create -----------------------------------------------------------------

# After a refused push and a rebase, a task with our ID may have arrived with
# no conflict at all (the file names differ): renumber our copy.
verify_create() {
  local out line
  [ -n "$(dup_ids HEAD)" ] || return 0
  out=$(cmd_renumber --amend) || return 1
  printf '%s\n' "$out"
  line=$(printf '%s\n' "$out" | grep "^renumbered TASK-$NEW_ID -> " || true)
  [ -n "$line" ] || return 0
  NEW_ID=$(printf '%s\n' "$line" | sed 's/^renumbered [^ ]* -> TASK-\([0-9]*\).*/\1/')
  git commit -q --amend -m "task-$NEW_ID: add task" \
    -m "$(git log -1 --format=%b)" || return 1
}

cmd_create() {
  local out file rc=0 offline=
  [ $# -gt 0 ] || usage
  cmd_sync || { rc=$?; [ "$rc" -eq 2 ] || return "$rc"; offline=1; }
  [ -n "$offline" ] || require_level
  out=$(backlog task create "$@" --plain) || die "backlog task create failed: $out"
  NEW_ID=$(printf '%s\n' "$out" | sed -n 's/^Created task [A-Za-z]*-\([0-9.]*\).*/\1/p' | head -1)
  [ -n "$NEW_ID" ] || NEW_ID=$(printf '%s\n' "$out" | sed -n 's/^Task [A-Za-z]*-\([0-9.]*\) - .*/\1/p' | head -1)
  [ -n "$NEW_ID" ] || die "cannot read the new task ID from: $out"
  file=$(task_file "$NEW_ID") || die "created TASK-$NEW_ID but cannot find its file"
  git add -- "$file"
  git commit -q -m "task-$NEW_ID: add task"
  if [ -n "$offline" ]; then
    echo "created TASK-$NEW_ID, provisional: not pushed (origin unreachable); run integrate when origin is back"
    return 0
  fi
  land_linear verify_create || rc=$?
  case "$rc" in
    0) echo "created TASK-$NEW_ID $(git rev-parse --short HEAD)" ;;
    2) echo "created TASK-$NEW_ID, provisional: not pushed (origin unreachable)" ;;
    *) die "TASK-$NEW_ID committed locally, provisional and not pushed" ;;
  esac
}

# --- integrate --------------------------------------------------------------

# run_checks MERGE_BASE — the checks integrate reruns on the merged tree.
# mycloud has no build, lint or test suite, so they are: no duplicate IDs,
# `bash -n` on touched shell scripts, and `ansible-playbook --syntax-check` on
# touched playbooks where Ansible is installed.
run_checks() {
  local mb=$1 f rc=0 changed
  if [ -n "${SHARED_BACKLOG_CHECKS:-}" ]; then
    sh -c "$SHARED_BACKLOG_CHECKS" || { say "checks failed: $SHARED_BACKLOG_CHECKS"; return 1; }
    return 0
  fi
  cmd_check_dupes HEAD || rc=1
  changed=$(git -c core.quotePath=false diff --name-only --diff-filter=d "$mb" HEAD)
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      *.sh|scripts/hooks/*) bash -n "$f" || { say "bash -n failed: $f"; rc=1; } ;;
      ansible/playbooks/*.yml)
        if command -v ansible-playbook >/dev/null 2>&1; then
          ansible-playbook --syntax-check "$f" >/dev/null || { say "syntax-check failed: $f"; rc=1; }
        else
          say "ansible-playbook not installed; skipped --syntax-check of $f"
        fi ;;
    esac
  done <<EOF
$changed
EOF
  return "$rc"
}

cmd_integrate() {
  local task='' try=1 rc local_sha remote_sha mb subject files err
  while [ $# -gt 0 ]; do
    case "$1" in
      --task) task=${2:?--task needs N}; task=${task#*-}; shift 2 ;;
      *) usage ;;
    esac
  done
  require_master_clean
  while :; do
    fetch_bounded || { say "done locally, not pushed"; return 2; }
    local_sha=$(git rev-parse HEAD)
    remote_sha=$(git rev-parse "$REMOTE/$BRANCH")
    if [ "$local_sha" = "$remote_sha" ]; then echo "origin already has $(git rev-parse --short HEAD)"; return 0; fi
    if git merge-base --is-ancestor HEAD "$REMOTE/$BRANCH"; then
      git merge -q --ff-only "$REMOTE/$BRANCH"
      echo "nothing to push; fast-forwarded to $(git rev-parse --short HEAD)"; return 0
    fi
    mb=$(git merge-base HEAD "$REMOTE/$BRANCH")
    if ! git merge-base --is-ancestor "$REMOTE/$BRANCH" HEAD; then
      # Merge, never rebase: a rebase would flatten Ralph's --no-ff merges.
      subject="Merge $REMOTE/$BRANCH into $BRANCH"
      [ -z "$task" ] || subject="task-$task: merge $REMOTE/$BRANCH"
      if ! err=$(git merge -q --no-ff -m "$subject" "$REMOTE/$BRANCH" 2>&1); then
        if ! git rev-parse -q --verify MERGE_HEAD >/dev/null; then
          # The merge never started (e.g. an untracked file in its way).
          printf '%s\n' "$err" >&2
          say "merge of $REMOTE/$BRANCH failed before it started, not pushed"
          return 1
        fi
        files=$(git diff --name-only --diff-filter=U | sed 's/^/  /')
        git merge --abort
        say "merge conflict with $REMOTE/$BRANCH, not pushed; merge aborted. Conflicting files:"
        printf '%s\n' "$files" >&2
        say "resolve only if mechanical: git merge $REMOTE/$BRANCH, fix, commit, rerun integrate; else stop and tell Paul"
        return 1
      fi
    fi
    cmd_renumber --amend >&2 || return 1
    run_checks "$mb" || { say "checks failed on the merged tree, not pushed; stop and tell Paul"; return 1; }
    rc=0; push_master || rc=$?
    case "$rc" in
      0) echo "pushed $(git rev-parse --short HEAD)"; return 0 ;;
      1) ;;
      2) say "done locally, not pushed"; return 2 ;;
      *) say "push rejected, not pushed; stop and tell Paul"; return 1 ;;
    esac
    [ "$try" -ge "$MAX_TRIES" ] && { say "push refused $MAX_TRIES times, not pushed; stop and tell Paul"; return 1; }
    try=$((try + 1))
  done
}

# --- install-hooks ----------------------------------------------------------

cmd_install_hooks() {
  local force='' src dst
  [ "${1:-}" = --force ] && force=1
  src="scripts/hooks/pre-push"
  [ -f "$src" ] || die "missing $src"
  dst="$(git rev-parse --git-path hooks)/pre-push"
  if [ -f "$dst" ] && ! grep -q "$HOOK_MARKER" "$dst" && [ -z "$force" ]; then
    die "$dst exists and is not ours; chain it by hand or pass --force"
  fi
  mkdir -p "${dst%/*}"
  cp "$src" "$dst"
  chmod +x "$dst"
  echo "installed $dst"
}

# --- main -------------------------------------------------------------------

[ $# -gt 0 ] || usage
cd "$(repo_root)"
cmd=$1; shift
case "$cmd" in
  sync) cmd_sync ;;
  claim) cmd_claim "$@" ;;
  release) cmd_release "$@" ;;
  create) cmd_create "$@" ;;
  integrate) cmd_integrate "$@" ;;
  check-dupes) cmd_check_dupes "$@" ;;
  renumber) cmd_renumber "$@" ;;
  install-hooks) cmd_install_hooks "$@" ;;
  -h|--help|help) usage ;;
  *) usage ;;
esac
