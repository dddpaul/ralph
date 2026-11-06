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
#                        create a task in a temporary worktree at a fresh
#                        origin/master and push it at once
#   integrate [--task N] land local master on origin: merge origin/master,
#                        renumber our duplicate IDs, rerun checks, push
#   check-dupes [REV]    exit 1 if REV's tree (default HEAD) has duplicate task
#                        or draft IDs, or backlog doctor fails on it
#   renumber [--base REF]
#                        renumber our copies of duplicate IDs (those not in REF,
#                        default origin/master) and commit
#   install-hooks [--force]
#                        install scripts/hooks/pre-push into .git/hooks
#   run-lock [--pid PID] take the run lock for a Ralph run owned by PID
#                        (default: the caller) and print its token
#   run-unlock [TOKEN]   release the run lock TOKEN (default
#                        $RALPH_RUN_LOCK_TOKEN) owns
#   unlock [--force] [protocol|run]
#                        remove a dead owner's lock; --force removes it
#                        whoever holds it
#
# The holder comes from --as, else $SHARED_BACKLOG_HOLDER, else
# `git config ralph.holder`; with none of them claim and release refuse. A bare
# @claude assignee names no host, so it counts as unassigned. Any other
# assignee besides the holder means the task is taken. $SHARED_BACKLOG_CHECKS,
# when set, replaces the checks integrate reruns (run with `sh -c` at the repo
# root).
#
# sync, claim, release, create, integrate and renumber hold the protocol lock,
# and refuse while a Ralph run holds the run lock unless $RALPH_RUN_LOCK_TOKEN
# carries that run's token. check-dupes takes no lock. Every subcommand that
# touches the network or the clone runs under a total deadline of
# $SHARED_BACKLOG_DEADLINE seconds (default 120); on expiry its process group
# is killed and the state is reported, not repaired.
#
# Exit codes: 0 ok, 1 refused / conflict / check failed, 2 origin unreachable,
# 64 usage error. Bash 3.2 clean: no associative arrays, no mapfile.

set -eu

REMOTE=origin
BRANCH=master
MAX_TRIES=3
HOOK_MARKER='shared-backlog pre-push hook'

die() { echo "shared-backlog: $*" >&2; exit 1; }
# help_text — the header comment from "Usage:" to its last line.
# SELF is absolute, so it still resolves after the cd to the repo root.
SELF="$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")"
help_text() { awk '/^# Usage:/ { p = 1 } p && !/^#/ { exit } p { sub(/^# ?/, ""); print }' "$SELF"; }
usage() { help_text >&2; exit 64; }
say() { echo "shared-backlog: $*" >&2; }

# Every network call is bounded and never prompts: BatchMode refuses SSH
# passphrase/password prompts, ConnectTimeout caps a dead host at 5 s, and the
# http.lowSpeed pair aborts a stalled HTTPS transfer after 10 s.
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${SHARED_BACKLOG_SSH:-ssh -o BatchMode=yes -o ConnectTimeout=5}"
net_git() { git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=10 "$@"; }

repo_root() { git rev-parse --show-toplevel; }

# task_prefix [REV] — the task prefix from the working tree's config, or from
# REV's tree when REV is given.
task_prefix() {
  local p
  if [ $# -gt 0 ]; then
    p=$(git show "$1:backlog/config.yml" 2>/dev/null | config_prefix)
  else
    p=$(config_prefix <backlog/config.yml 2>/dev/null)
  fi
  echo "${p:-task}"
}

config_prefix() {
  sed -n 's/^task_prefix: *["'\'']\{0,1\}\([^"'\'']*\)["'\'']\{0,1\} *$/\1/p' | head -1
}

# --- locks ------------------------------------------------------------------

# Both locks are directories under the canonical git common dir, so every
# worktree of a clone shares them: the protocol lock serializes the mutating
# subcommands, and the run lock admits one Ralph run per clone. mkdir is the
# atomic step; the owner file inside says who holds the lock.

# lock_path KIND — the lock directory of KIND (protocol or run).
lock_path() { echo "$LOCK_BASE/shared-backlog-$1.lock"; }

new_token() { od -An -tx1 -N16 /dev/urandom | tr -d ' \n'; }
container_flag() { if [ -f /.dockerenv ] || [ -f /run/.containerenv ]; then echo 1; else echo 0; fi; }
pid_ns() { readlink /proc/self/ns/pid 2>/dev/null || echo none; }

# pid_alive PID — 0 unless PID provably no longer exists. A pid we may not
# signal still exists, and without ps we cannot tell, so it counts as alive.
pid_alive() {
  kill -0 "$1" 2>/dev/null && return 0
  command -v ps >/dev/null 2>&1 || return 0
  ps -p "$1" >/dev/null 2>&1
}

# lock_field KIND KEY — a value from KIND's owner file, empty when absent.
lock_field() { sed -n "s/^$2=//p" "$(lock_path "$1")/owner" 2>/dev/null | head -1; }

# lock_try KIND TOKEN PID — take KIND if it is free: 0 taken, 1 held.
lock_try() {
  local l
  l=$(lock_path "$1")
  mkdir "$l" 2>/dev/null || return 1
  printf 'token=%s\nhost=%s\ncontainer=%s\npidns=%s\npid=%s\nstarted=%s\ncommand=%s\n' \
    "$2" "$(uname -n)" "$(container_flag)" "$(pid_ns)" "$3" "$(date +%s)" "$CMD" \
    >"$l/owner.tmp" && mv "$l/owner.tmp" "$l/owner" ||
    { rm -rf "$l"; die "cannot write the owner file of $l"; }
}

# lock_release KIND TOKEN — remove KIND only when TOKEN owns it.
lock_release() {
  [ -n "$2" ] && [ "$(lock_field "$1" token)" = "$2" ] || return 1
  rm -rf "$(lock_path "$1")"
}

# lock_reclaimable KIND — 0 when KIND's owner provably died: it ran on this
# host in this pid namespace, and its pid is gone. Any other lock (another
# host, the other side of a container boundary, no owner file) is reported
# and needs unlock --force.
lock_reclaimable() {
  local pid
  pid=$(lock_field "$1" pid)
  case "$pid" in ''|*[!0-9]*) return 1 ;; esac
  [ "$(lock_field "$1" host)" = "$(uname -n)" ] || return 1
  [ "$(lock_field "$1" container)" = "$(container_flag)" ] || return 1
  [ "$(lock_field "$1" pidns)" = "$(pid_ns)" ] || return 1
  ! pid_alive "$pid"
}

# lock_reclaim KIND TOKEN — remove a dead owner's lock. Two contenders can both
# judge TOKEN's lock stale; the marker directory named after TOKEN lets one at
# a time recheck that TOKEN still owns the lock, so a late contender never
# removes the lock the winner has taken since. 0 removed, 1 not.
lock_reclaim() {
  local l m rc=1 pid
  l=$(lock_path "$1")
  m="$l.reclaim-$2"
  mkdir "$m" 2>/dev/null || return 1
  if [ "$(lock_field "$1" token)" = "$2" ] && lock_reclaimable "$1"; then
    pid=$(lock_field "$1" pid)
    rm -rf "$l"
    rc=0
    say "reclaimed the $1 lock of dead pid $pid"
  fi
  rmdir "$m" 2>/dev/null || true
  return "$rc"
}

lock_report() {
  local l
  l=$(lock_path "$1")
  if [ -z "$(lock_field "$1" token)" ]; then
    say "the $1 lock $l has no owner file"
  else
    say "the $1 lock is held by pid $(lock_field "$1" pid) on $(lock_field "$1" host)" \
      "(container=$(lock_field "$1" container), $(lock_field "$1" pidns))," \
      "running $(lock_field "$1" command) since $(lock_field "$1" started)"
  fi
  say "if that owner is gone, remove the lock with: shared-backlog.sh unlock --force $1"
}

# lock_acquire KIND TOKEN PID UNTIL — take KIND, reclaiming a dead owner's
# lock and waiting for a live owner until epoch second UNTIL. 0 taken, 1 not.
lock_acquire() {
  local tok waited=''
  while :; do
    lock_try "$1" "$2" "$3" && return 0
    tok=$(lock_field "$1" token)
    if [ -n "$tok" ] && lock_reclaimable "$1"; then
      # Tests widen the window between the stale check and the reclaim.
      [ -z "${SHARED_BACKLOG_TEST_RECLAIM_PAUSE:-}" ] || sleep "$SHARED_BACKLOG_TEST_RECLAIM_PAUSE"
      lock_reclaim "$1" "$tok" && continue
    fi
    if [ "$(date +%s)" -ge "$4" ]; then
      [ -d "$(lock_path "$1")" ] || continue
      lock_report "$1"
      return 1
    fi
    [ -n "$waited" ] || { say "waiting for the $1 lock (pid $(lock_field "$1" pid))"; waited=1; }
    sleep 1
  done
}

# run_lock_gate — while a Ralph run holds the run lock, only that run (its
# token in RALPH_RUN_LOCK_TOKEN) may run a mutating subcommand.
run_lock_gate() {
  local tok
  [ -d "$(lock_path run)" ] || return 0
  tok=$(lock_field run token)
  [ -n "$tok" ] && [ "${RALPH_RUN_LOCK_TOKEN:-}" = "$tok" ] && return 0
  [ -n "$tok" ] && lock_reclaimable run && lock_reclaim run "$tok" && return 0
  [ -d "$(lock_path run)" ] || return 0
  say "refusing $CMD: a Ralph run holds the run lock; its own calls carry RALPH_RUN_LOCK_TOKEN"
  lock_report run
  return 1
}

cmd_run_lock() {
  local pid=$PPID tok
  while [ $# -gt 0 ]; do
    case "$1" in
      --pid) pid=${2:?--pid needs a pid}; shift 2 ;;
      *) usage ;;
    esac
  done
  case "$pid" in ''|*[!0-9]*) usage ;; esac
  tok=$(new_token)
  lock_acquire run "$tok" "$pid" "$(date +%s)" || die "run lock not taken"
  echo "$tok"
}

cmd_run_unlock() {
  local tok=${1:-${RALPH_RUN_LOCK_TOKEN:-}}
  [ $# -le 1 ] && [ -n "$tok" ] || usage
  lock_release run "$tok" || die "the run lock is not held by that token"
  say "released the run lock"
}

cmd_unlock() {
  local force='' kinds='protocol run' k tok rc=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --force) force=1; shift ;;
      protocol|run) kinds=$1; shift ;;
      *) usage ;;
    esac
  done
  for k in $kinds; do
    [ -d "$(lock_path "$k")" ] || continue
    if [ -n "$force" ]; then
      rm -rf "$(lock_path "$k")" "$(lock_path "$k")".reclaim-*
      say "removed the $k lock"
      continue
    fi
    tok=$(lock_field "$k" token)
    if [ -n "$tok" ] && lock_reclaimable "$k" && lock_reclaim "$k" "$tok"; then continue; fi
    lock_report "$k"
    rc=1
  done
  return "$rc"
}

# --- deadlines --------------------------------------------------------------

# git_state — a one-line summary of what a killed subcommand left behind.
git_state() {
  local gd s
  gd=$(git rev-parse --git-dir)
  s="on $(git symbolic-ref --short -q HEAD || echo 'detached HEAD') at $(git rev-parse --short HEAD 2>/dev/null)"
  if [ -f "$gd/MERGE_HEAD" ]; then s="$s, merge in progress"; fi
  if [ -d "$gd/rebase-merge" ] || [ -d "$gd/rebase-apply" ]; then s="$s, rebase in progress"; fi
  if [ -f "$gd/index.lock" ]; then s="$s, $gd/index.lock left by a killed git"; fi
  if [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then s="$s, uncommitted changes"; fi
  echo "$s"
}

# on_signal CODE — kill the running subcommand's group and exit; the EXIT trap
# then releases our own lock.
on_signal() {
  [ -z "$CHILD_PID" ] || kill -TERM -- "-$CHILD_PID" 2>/dev/null || true
  exit "$1"
}

# with_deadline FN ARGS... — run FN in a subshell that leads its own process
# group, and kill the group once epoch second DEADLINE_AT passes. Our own lock
# is held by this shell, outside the group, so a kill cannot strand it.
with_deadline() {
  local flag watchdog rc=0
  flag=$(mktemp "${TMPDIR:-/tmp}/shared-backlog-deadline.XXXXXX")
  set -m
  ("$@") &
  CHILD_PID=$!
  set +m
  (
    while [ "$(date +%s)" -lt "$DEADLINE_AT" ]; do sleep 1; done
    echo expired >"$flag"
    kill -TERM -- "-$CHILD_PID" 2>/dev/null || true
  ) </dev/null >/dev/null 2>&1 &
  watchdog=$!
  wait "$CHILD_PID" || rc=$?
  kill "$watchdog" 2>/dev/null || true
  wait "$watchdog" 2>/dev/null || true
  if [ -s "$flag" ]; then
    kill -KILL -- "-$CHILD_PID" 2>/dev/null || true
    say "$CMD ran past its ${DEADLINE}s deadline (SHARED_BACKLOG_DEADLINE); killed its process group"
    say "state left as is: $(git_state)"
    rc=1
  fi
  CHILD_PID=''
  rm -f "$flag"
  return "$rc"
}

# protocol_cmd FN ARGS... — a mutating subcommand: take the protocol lock, pass
# the run-lock gate, run FN under the deadline, release only our own lock.
protocol_cmd() {
  PROTOCOL_TOKEN=$(new_token)
  lock_acquire protocol "$PROTOCOL_TOKEN" "$$" "$DEADLINE_AT" || exit 1
  run_lock_gate || exit 1
  with_deadline "$@"
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

# tree_task_ids REV [PREFIX] — "ID<TAB>path" for every task file in REV's tree;
# PREFIX defaults to the working tree's task prefix.
tree_task_ids() {
  tree_ids "$1" "${2:-$(task_prefix)}" backlog/tasks backlog/completed backlog/archive/tasks
}

# tree_draft_ids REV — "ID<TAB>path" for every draft in REV's tree. Drafts have
# their own ID space under the fixed prefix "draft".
tree_draft_ids() { tree_ids "$1" draft backlog/drafts backlog/archive/drafts; }

# tree_ids REV PREFIX DIR... — "ID<TAB>path" for every PREFIX-N file under the
# DIRs of REV's tree.
tree_ids() {
  local rev=$1 pfx=$2
  shift 2
  git -c core.quotePath=false ls-tree -r --name-only "$rev" -- "$@" 2>/dev/null |
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

# require_no_untracked_tasks — refuse while the working tree holds an untracked
# task file: create publishes IDs from a temporary worktree, so a task file
# made outside it carries an ID nobody else can see, and a later pull may bring
# the same ID from origin.
require_no_untracked_tasks() {
  local files
  files=$(git -c core.quotePath=false ls-files --others --exclude-standard -- \
    backlog/tasks backlog/completed backlog/archive/tasks | grep '\.md$' || true)
  [ -n "$files" ] || return 0
  say "untracked task files in the working tree; publish tasks with create, and move or remove these first:"
  printf '%s\n' "$files" | sed 's/^/  /' >&2
  exit 1
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
  require_no_untracked_tasks
  fetch_bounded || return 2
  git merge -q --ff-only "$REMOTE/$BRANCH" 2>/dev/null ||
    die "local $BRANCH has diverged from $REMOTE/$BRANCH; run integrate first"
  say "synced to $(git rev-parse --short HEAD)"
}

# require_level — local master carries nothing origin lacks. claim and release
# retry and undo with a reset to origin/master; with unpushed work (an
# un-integrated Ralph run) on master, the reset would drop it.
require_level() {
  [ "$(git rev-parse HEAD)" = "$(git rev-parse "$REMOTE/$BRANCH")" ] ||
    die "local $BRANCH is ahead of $REMOTE/$BRANCH; run integrate first"
}

# --- duplicate IDs ----------------------------------------------------------

# dup_ids REV — the IDs that more than one task file in REV's tree carries.
dup_ids() { tree_task_ids "$1" | cut -f1 | sort | uniq -d; }

# report_dupes KIND LISTING — name each ID that more than one line of LISTING
# ("ID<TAB>path") carries; 1 when there is one.
report_dupes() {
  local dups id
  dups=$(printf '%s\n' "$2" | cut -f1 | sort | uniq -d | grep . || true)
  [ -n "$dups" ] || return 0
  say "duplicate $1 IDs in $REV:"
  for id in $dups; do
    printf '%s\n' "$2" | awk -F'\t' -v id="$id" '$1 == id { print "  " $2 }' >&2
  done
  return 1
}

# cmd_check_dupes [REV] — check REV's tree alone: its task prefix and config
# come from REV, never from the working tree.
cmd_check_dupes() {
  local tmp rc=0
  REV=${1:-HEAD}
  [ $# -le 1 ] || usage
  git rev-parse -q --verify "$REV^{tree}" >/dev/null || die "unknown revision: $REV"
  if ! git cat-file -e "$REV:backlog" 2>/dev/null; then
    say "$REV has no backlog/ directory; no task IDs to check"
    return 0
  fi
  command -v backlog >/dev/null 2>&1 || die "backlog not on PATH; cannot run backlog doctor on $REV"
  report_dupes task "$(tree_task_ids "$REV" "$(task_prefix "$REV")")" || rc=1
  report_dupes draft "$(tree_draft_ids "$REV")" || rc=1
  # backlog doctor also sees documents, decisions and drafts, and dependency
  # cycles; run it on an export of exactly this tree, not the working tree.
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog.XXXXXX")
  git archive "$REV" backlog | tar -x -C "$tmp"
  if ! (cd "$tmp" && backlog doctor >"$tmp/.doctor.out" 2>&1); then
    sed 's/^/  doctor: /' "$tmp/.doctor.out" >&2
    rc=1
  fi
  rm -rf "$tmp"
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
# duplicate ever reaches origin (integrate amends its merge commit).
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

# --- landing by refetch and reapply (claim, release, create) ----------------

# land_reapply APPLY — run APPLY (a function name) on top of origin/master and
# push the commit it makes. APPLY checks the current tree and commits, returns
# 0 when it committed, 4 when it refuses or fails (it says why) and 5 when the
# tree already says what it would commit. When the push is refused, fetch, drop
# our unpushed commit by resetting to the new origin/master and run APPLY
# again, at most MAX_TRIES pushes. APPLY runs under `||`, so set -e is off in it.
# A failed fetch keeps the unpushed commit.
# Returns 0 pushed, 2 unreachable, 3 push rejected or refused MAX_TRIES times,
# 4 APPLY refused, 5 nothing to push. The caller resets to origin on failure.
land_reapply() {
  local apply=$1 try=1 rc
  while :; do
    rc=0; "$apply" || rc=$?
    [ "$rc" -eq 0 ] || return "$rc"
    rc=0; push_master || rc=$?
    case "$rc" in
      0) return 0 ;;
      1) ;;
      *) return "$rc" ;;
    esac
    [ "$try" -ge "$MAX_TRIES" ] && { say "push refused $MAX_TRIES times"; return 3; }
    try=$((try + 1))
    fetch_bounded || return 2
    git reset -q --hard "$REMOTE/$BRANCH"
  done
}

# --- claim / release --------------------------------------------------------

# holder_from_args ARGS... — set TASK_ID, FORCE and HOLDER: --as, else
# $SHARED_BACKLOG_HOLDER, else git config ralph.holder.
holder_from_args() {
  HOLDER=
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
  [ -n "$HOLDER" ] || HOLDER=${SHARED_BACKLOG_HOLDER:-}
  [ -n "$HOLDER" ] || HOLDER=$(git config --get ralph.holder || true)
  [ -n "$HOLDER" ] ||
    die "no holder: pass --as @name, set SHARED_BACKLOG_HOLDER or git config ralph.holder"
  case "$HOLDER" in @*) ;; *) HOLDER="@$HOLDER" ;; esac
  [ "$HOLDER" != @claude ] || die "the holder @claude names no host; pick a per-host name"
}

assignees() { local f; f=$(task_file "$1") || return 0; fm_list "$f" assignee; }

# real_assignees N — TASK-N's assignees without a bare @claude, which names no
# host and so counts as unassigned.
real_assignees() { assignees "$1" | grep -vxE '@?claude' || true; }

# other_assignees N — TASK-N's assignees besides the holder, space-separated.
other_assignees() {
  local who
  who=$(real_assignees "$1" | grep -vxF -e "$HOLDER" | tr '\n' ' ')
  echo "${who% }"
}

held_by_holder() { real_assignees "$1" | grep -qxF -e "$HOLDER"; }

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

# claim_apply — check TASK_ID against the current tree and commit the claim.
claim_apply() {
  local f who st
  f=$(task_file "$TASK_ID") || { say "TASK-$TASK_ID not found"; return 4; }
  who=$(other_assignees "$TASK_ID")
  [ -z "$who" ] || { say "TASK-$TASK_ID taken by $who"; return 4; }
  # A claim we already hold passes the same status and dependency checks.
  st=$(fm_scalar "$f" status)
  [ "$st" = "To Do" ] || { say "TASK-$TASK_ID is '$st', not To Do"; return 4; }
  if [ -z "$FORCE" ] && ! deps_done "$TASK_ID"; then
    say "claim refused; --force overrides on Paul's say-so"
    return 4
  fi
  held_by_holder "$TASK_ID" && return 5
  # -a replaces the whole list, so a bare @claude goes with it.
  backlog task edit "$TASK_ID" -a "$HOLDER" >/dev/null &&
    git add -- "$(task_file "$TASK_ID")" &&
    git commit -q -m "task-$TASK_ID: claim for $HOLDER" ||
    { say "committing the claim of TASK-$TASK_ID failed"; return 4; }
}

cmd_claim() {
  local rc=0
  holder_from_args "$@"
  cmd_sync || { rc=$?; [ "$rc" -eq 2 ] && say "cannot claim TASK-$TASK_ID: a claim nobody can see protects nothing"; return "$rc"; }
  require_level
  land_reapply claim_apply || rc=$?
  case "$rc" in
    0) echo "claimed TASK-$TASK_ID $(git rev-parse --short HEAD)"; return 0 ;;
    5) say "TASK-$TASK_ID is already claimed by $HOLDER"; return 0 ;;
  esac
  # The claim did not land: drop it. Before it the tree was clean and level
  # with origin, so going to origin's tip loses nothing. After the last refused
  # push, fetch once more so that the tip is the one that won.
  [ "$rc" -ne 3 ] || fetch_bounded || true
  git reset -q --hard "$REMOTE/$BRANCH"
  case "$rc" in
    2) say "claim not pushed (origin unreachable); undone locally"; exit 2 ;;
    3) die "claim push rejected; undone locally" ;;
  esac
  exit 1
}

# release_apply — check TASK_ID against the current tree and commit the release.
release_apply() {
  local f who
  f=$(task_file "$TASK_ID") || { say "TASK-$TASK_ID not found"; return 4; }
  who=$(real_assignees "$TASK_ID" | tr '\n' ' ')
  who=${who% }
  [ -n "$who" ] || { say "TASK-$TASK_ID has no assignee"; return 5; }
  if [ "$who" != "$HOLDER" ] && [ -z "$FORCE" ]; then
    say "TASK-$TASK_ID is held by $who, not $HOLDER; --force overrides on Paul's say-so"
    return 4
  fi
  backlog task edit "$TASK_ID" -a "" >/dev/null &&
    git add -- "$f" &&
    git commit -q -m "task-$TASK_ID: release from $who" ||
    { say "committing the release of TASK-$TASK_ID failed"; return 4; }
}

cmd_release() {
  local rc=0
  holder_from_args "$@"
  cmd_sync || return $?
  require_level
  land_reapply release_apply || rc=$?
  case "$rc" in
    0) echo "released TASK-$TASK_ID $(git rev-parse --short HEAD)"; return 0 ;;
    5) return 0 ;;
  esac
  [ "$rc" -ne 3 ] || fetch_bounded || true
  git reset -q --hard "$REMOTE/$BRANCH"
  case "$rc" in
    2) say "release not pushed (origin unreachable); undone locally"; exit 2 ;;
    3) die "release push rejected; undone locally" ;;
  esac
  exit 1
}

# --- create -----------------------------------------------------------------

# create_apply — create the task from CREATE_ARGS on the current tree and
# commit it with the Shared-Backlog-Op trailer OP_ID; after a refused push the
# fresh tree gives it the next free ID, while OP_ID stays the same.
create_apply() {
  local out file
  out=$(backlog task create "${CREATE_ARGS[@]}" --plain) || { say "backlog task create failed: $out"; return 4; }
  NEW_ID=$(printf '%s\n' "$out" | sed -n 's/^Created task [A-Za-z]*-\([0-9.]*\).*/\1/p' | head -1)
  [ -n "$NEW_ID" ] || NEW_ID=$(printf '%s\n' "$out" | sed -n 's/^Task [A-Za-z]*-\([0-9.]*\) - .*/\1/p' | head -1)
  [ -n "$NEW_ID" ] || { say "cannot read the new task ID from: $out"; return 4; }
  file=$(task_file "$NEW_ID") || { say "created TASK-$NEW_ID but cannot find its file"; return 4; }
  git add -- "$file" && git commit -q -m "task-$NEW_ID: add task" -m "Shared-Backlog-Op: $OP_ID" ||
    { say "committing TASK-$NEW_ID failed"; return 4; }
}

# create_cleanup — remove the temporary worktree create allocated in.
create_cleanup() {
  [ -n "$CREATE_TMP" ] || return 0
  git -C "$CREATE_ROOT" worktree remove --force "$CREATE_TMP/wt" 2>/dev/null || true
  rm -rf "$CREATE_TMP"
  git -C "$CREATE_ROOT" worktree prune 2>/dev/null || true
  CREATE_TMP=''
}

# cmd_create ARGS... — allocate a task ID in a detached temporary worktree at a
# freshly fetched origin/master and push it, so the ID is on origin before
# anyone sees it. The user's branch, index and working tree are never touched,
# whatever state they are in; `sync` brings the task in.
cmd_create() {
  local rc=0
  [ $# -gt 0 ] || usage
  CREATE_ARGS=("$@")
  # The operation ID, not the task ID, is fixed once per create.
  OP_ID=$(new_token)
  CREATE_ROOT=$(pwd -P)
  CREATE_TMP=''
  fetch_bounded || { say "create refused: a task ID nobody can see is not allocated; nothing created"; exit 2; }
  CREATE_TMP=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-create.XXXXXX")
  trap create_cleanup EXIT
  git worktree add -q --detach "$CREATE_TMP/wt" "$REMOTE/$BRANCH" ||
    die "cannot add a temporary worktree at $REMOTE/$BRANCH"
  cd "$CREATE_TMP/wt"
  land_reapply create_apply || rc=$?
  cd "$CREATE_ROOT"
  case "$rc" in
    0) echo "created TASK-$NEW_ID $(git rev-parse --short "$REMOTE/$BRANCH") (Shared-Backlog-Op: $OP_ID); run sync to bring it in" ;;
    2) say "TASK-${NEW_ID:-?} not pushed (origin unreachable); nothing created locally"; exit 2 ;;
    4) exit 1 ;;
    *) die "TASK-${NEW_ID:-?} not pushed; nothing created locally" ;;
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
  require_no_untracked_tasks
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
case "$1" in -h|--help|help) help_text; exit 0 ;; esac
cd "$(repo_root)"
CMD=$1; shift
LOCK_BASE=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
DEADLINE=${SHARED_BACKLOG_DEADLINE:-120}
case "$DEADLINE" in
  ''|*[!0-9]*|0) say "SHARED_BACKLOG_DEADLINE must be a whole number of seconds above 0, not '$DEADLINE'"; exit 64 ;;
esac
DEADLINE_AT=$(($(date +%s) + DEADLINE))
CHILD_PID=''
PROTOCOL_TOKEN=''
trap 'lock_release protocol "$PROTOCOL_TOKEN" || true' EXIT
trap 'on_signal 129' HUP
trap 'on_signal 130' INT
trap 'on_signal 143' TERM
case "$CMD" in
  sync) protocol_cmd cmd_sync "$@" ;;
  claim) protocol_cmd cmd_claim "$@" ;;
  release) protocol_cmd cmd_release "$@" ;;
  create) protocol_cmd cmd_create "$@" ;;
  integrate) protocol_cmd cmd_integrate "$@" ;;
  renumber) protocol_cmd cmd_renumber "$@" ;;
  check-dupes) with_deadline cmd_check_dupes "$@" ;;
  install-hooks) cmd_install_hooks "$@" ;;
  run-lock)
    # The protocol lock orders taking the run lock against the gate above.
    PROTOCOL_TOKEN=$(new_token)
    lock_acquire protocol "$PROTOCOL_TOKEN" "$$" "$DEADLINE_AT" || exit 1
    cmd_run_lock "$@" ;;
  run-unlock) cmd_run_unlock "$@" ;;
  unlock) cmd_unlock "$@" ;;
  *) usage ;;
esac
