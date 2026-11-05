#!/usr/bin/env bash
# Scratch-repo tests for the lock primitives and deadlines of
# plugins/ralph/scripts/shared-backlog.sh (TASK-304). Everything runs in a
# `mktemp -d`: one bare repo stands in for origin and one clone for a host.
# Never touches a real origin and needs no backlog CLI.
#
# Usage: bash tests/shell/shared-backlog-lock-test.sh

set -u

SB="$(cd "$(dirname "$0")/../.." && pwd)/plugins/ralph/scripts/shared-backlog.sh"
work=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-lock-test.XXXXXX")
trap 'rm -rf "$work"' EXIT

# Isolate git from the user's config (hooksPath, signing, identity).
export HOME="$work/home"
export GIT_CONFIG_NOSYSTEM=1
unset RALPH_RUN_LOCK_TOKEN SHARED_BACKLOG_DEADLINE SHARED_BACKLOG_SSH GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
mkdir -p "$HOME"
git config --global user.name tester
git config --global user.email tester@example.invalid
git config --global init.defaultBranch master

pass=0
fail=0
ok() { pass=$((pass + 1)); echo "ok   - $*"; }
nok() { fail=$((fail + 1)); echo "FAIL - $*"; }
check() { local d=$1; shift; if "$@"; then ok "$d"; else nok "$d"; fi; }

# fresh — rebuild origin.git and the clone a.
fresh() {
  rm -rf "$work/origin.git" "$work/seed" "$work/a" "$work/wt"
  git init -q --bare "$work/origin.git"
  mkdir -p "$work/seed/backlog/tasks"
  printf 'task_prefix: "task"\n' >"$work/seed/backlog/config.yml"
  touch "$work/seed/backlog/tasks/.gitkeep"
  (cd "$work/seed" && git init -q && git add -A && git commit -q -m init &&
    git remote add origin "$work/origin.git" && git push -q origin master) ||
    { echo "seed failed"; exit 1; }
  git clone -q "$work/origin.git" "$work/a"
}

sb() { (cd "$work/a" && bash "$SB" "$@"); }
lockdir() { echo "$work/a/.git/shared-backlog-$1.lock"; }
field() { sed -n "s/^$2=//p" "$(lockdir "$1")/owner"; }
container_flag() { if [ -f /.dockerenv ] || [ -f /run/.containerenv ]; then echo 1; else echo 0; fi; }
pid_ns() { readlink /proc/self/ns/pid 2>/dev/null || echo none; }

# dead_pid — a pid that existed and is gone.
dead_pid() { local p; sh -c 'exit 0' & p=$!; wait "$p"; echo "$p"; }

# plant KIND TOKEN PID [HOST [PIDNS]] — a lock dir with a hand-written owner.
plant() {
  mkdir -p "$(lockdir "$1")"
  printf 'token=%s\nhost=%s\ncontainer=%s\npidns=%s\npid=%s\nstarted=%s\ncommand=test\n' \
    "$2" "${4:-$(uname -n)}" "$(container_flag)" "${5:-$(pid_ns)}" "$3" "$(date +%s)" \
    >"$(lockdir "$1")/owner"
}

# hang_origin — point origin at an ssh stand-in that records its pid and hangs.
hang_origin() {
  printf '#!/bin/sh\necho $$ >"%s/ssh.pid"\nexec sleep 60\n' "$work" >"$work/fake-ssh"
  chmod +x "$work/fake-ssh"
  rm -f "$work/ssh.pid"
  (cd "$work/a" && git remote set-url origin ssh://example.invalid/x.git)
}

# --- acquire and release ----------------------------------------------------

fresh
tok=$(sb run-lock --pid $$ 2>/dev/null)
check "run-lock prints a 32-hex token" sh -c 'printf "%s" "$1" | grep -Eq "^[0-9a-f]{32}$"' _ "$tok"
check "run lock is a directory under the git common dir" test -d "$(lockdir run)"
check "owner file holds the token" test "$(field run token)" = "$tok"
check "owner file holds the host" test "$(field run host)" = "$(uname -n)"
check "owner file holds the container flag" test "$(field run container)" = "$(container_flag)"
check "owner file holds the pid namespace" test "$(field run pidns)" = "$(pid_ns)"
check "owner file holds the pid" test "$(field run pid)" = "$$"
check "owner file holds the start time" sh -c 'case "$1" in ""|*[!0-9]*) exit 1;; esac' _ "$(field run started)"
check "a second run-lock is refused while the first holds it" sh -c '! (cd "$1" && bash "$2" run-lock --pid $$) 2>/dev/null' _ "$work/a" "$SB"
check "the refused run-lock leaves the owner alone" test "$(field run token)" = "$tok"

# --- token mismatch ---------------------------------------------------------

check "run-unlock with a foreign token fails" sh -c '! (cd "$1" && bash "$2" run-unlock deadbeef) 2>/dev/null' _ "$work/a" "$SB"
check "a foreign token leaves the lock in place" test -d "$(lockdir run)"
check "run-unlock with the owner's token releases" sb run-unlock "$tok"
check "the run lock is gone after release" test ! -d "$(lockdir run)"
tok=$(sb run-lock --pid $$ 2>/dev/null)
check "run-unlock reads RALPH_RUN_LOCK_TOKEN" sh -c '(cd "$1" && RALPH_RUN_LOCK_TOKEN=$3 bash "$2" run-unlock) 2>/dev/null' _ "$work/a" "$SB" "$tok"

# The protocol lock exists only while a mutating subcommand runs.
check "sync succeeds and leaves no protocol lock" sh -c '(cd "$1" && bash "$2" sync) 2>/dev/null && test ! -d "$3"' _ "$work/a" "$SB" "$(lockdir protocol)"

# --- canonical git common dir ----------------------------------------------

(cd "$work/a" && git worktree add -q -b side "$work/wt")
wtok=$( (cd "$work/wt" && bash "$SB" run-lock --pid $$) 2>/dev/null)
check "a linked worktree takes the lock under the main common dir" test "$(field run token)" = "$wtok"
check "no lock lands in the worktree's own git dir" sh -c '! ls -d "$1"/.git/worktrees/wt/shared-backlog-* 2>/dev/null' _ "$work/a"
sb run-unlock "$wtok" 2>/dev/null

# --- stale locks ------------------------------------------------------------

fresh
plant run stale1 "$(dead_pid)"
tok=$(sb run-lock --pid $$ 2>/dev/null)
check "a dead owner's run lock on this host is reclaimed" test -n "$tok" -a "$(field run token)" = "$tok"
sb run-unlock "$tok" 2>/dev/null

plant protocol stale2 "$(dead_pid)"
check "a dead owner's protocol lock is reclaimed by sync" sh -c '(cd "$1" && bash "$2" sync) 2>/dev/null && test ! -d "$3"' _ "$work/a" "$SB" "$(lockdir protocol)"

plant run other "$(dead_pid)" some-other-host
out=$(sb run-lock --pid $$ 2>&1); rc=$?
check "a lock from another host is not reclaimed" test "$rc" -eq 1 -a "$(field run token)" = other
check "the refusal names unlock --force" sh -c 'printf "%s" "$1" | grep -q "unlock --force run"' _ "$out"
check "unlock without --force keeps another host's lock" sh -c '! (cd "$1" && bash "$2" unlock run) 2>/dev/null && test -d "$3"' _ "$work/a" "$SB" "$(lockdir run)"
check "unlock --force removes it" sh -c '(cd "$1" && bash "$2" unlock --force run) 2>/dev/null && test ! -d "$3"' _ "$work/a" "$SB" "$(lockdir run)"

plant run otherns "$(dead_pid)" "" "pid:[1]"
check "a lock from another pid namespace is not reclaimed" sh -c '! (cd "$1" && bash "$2" run-lock --pid $$) 2>/dev/null && test "$(sed -n "s/^token=//p" "$3/owner")" = otherns' _ "$work/a" "$SB" "$(lockdir run)"
sb unlock --force run 2>/dev/null

plant run alive $$
check "a live owner's lock is not reclaimed" sh -c '! (cd "$1" && bash "$2" run-lock --pid $$) 2>/dev/null && test "$(sed -n "s/^token=//p" "$3/owner")" = alive' _ "$work/a" "$SB" "$(lockdir run)"
sb unlock --force run 2>/dev/null

mkdir "$(lockdir run)"
check "a lock with no owner file is not reclaimed" sh -c '! (cd "$1" && bash "$2" run-lock --pid $$) 2>/dev/null && test -d "$3"' _ "$work/a" "$SB" "$(lockdir run)"
sb unlock --force run 2>/dev/null

plant run stale3 "$(dead_pid)"
check "unlock without --force reclaims a dead owner's lock" sh -c '(cd "$1" && bash "$2" unlock run) 2>/dev/null && test ! -d "$3"' _ "$work/a" "$SB" "$(lockdir run)"

# --- the reclaim race -------------------------------------------------------

# Two syncs find one stale protocol lock. Both judge it stale and pause before
# reclaiming it; the second pauses longer, so it reclaims after the first has
# taken the lock. The ssh stand-in marks any overlap of the two lock holders.
printf '#!/bin/sh\nmkdir "%s/inside" 2>/dev/null || touch "%s/overlap"\nsleep 2\nrmdir "%s/inside"\nexit 1\n' \
  "$work" "$work" "$work" >"$work/crit-ssh"
chmod +x "$work/crit-ssh"
(cd "$work/a" && git remote set-url origin ssh://example.invalid/x.git)
race_ok=1
for i in 1 2 3; do
  rm -rf "$work/inside" "$work/overlap"
  plant protocol "race$i" "$(dead_pid)"
  for n in 1 2; do
    (cd "$work/a" && SHARED_BACKLOG_SSH="$work/crit-ssh" SHARED_BACKLOG_TEST_RECLAIM_PAUSE=$n \
      SHARED_BACKLOG_DEADLINE=20 bash "$SB" sync >/dev/null 2>"$work/race$n.err") &
  done
  wait
  reclaims=$(cat "$work/race1.err" "$work/race2.err" | grep -c "reclaimed the protocol lock")
  if [ -e "$work/overlap" ] || [ "$reclaims" -ne 1 ] || [ -d "$(lockdir protocol)" ]; then
    race_ok=''; echo "  round $i: reclaims=$reclaims overlap=$([ -e "$work/overlap" ] && echo yes || echo no)"
  fi
done
check "two contenders reclaiming one stale lock never both hold it (3 rounds)" test -n "$race_ok"

# Two run-locks on one stale run lock: exactly one takes it.
plant run racerun "$(dead_pid)"
for n in 1 2; do
  (cd "$work/a" && SHARED_BACKLOG_TEST_RECLAIM_PAUSE=$n bash "$SB" run-lock --pid $$ >"$work/r$n" 2>/dev/null
    echo $? >"$work/r$n.rc") &
done
wait
wins=0; winner=''
for n in 1 2; do
  if [ "$(cat "$work/r$n.rc")" = 0 ]; then wins=$((wins + 1)); winner=$(cat "$work/r$n"); fi
done
check "two run-locks on one stale run lock: exactly one wins" test "$wins" -eq 1 -a "$(field run token)" = "$winner"
sb unlock --force run 2>/dev/null

# --- the run-lock gate ------------------------------------------------------

fresh
tok=$(sb run-lock --pid $$ 2>/dev/null)
head0=$(cd "$work/a" && git rev-parse HEAD)
for c in "sync" "claim 1 --as @x" "release 1 --as @x" "create Gated" "integrate" "renumber"; do
  # shellcheck disable=SC2086
  out=$(cd "$work/a" && bash "$SB" $c 2>&1); rc=$?
  check "$c refuses while a run holds the run lock" sh -c 'test "$1" -eq 1 && printf "%s" "$2" | grep -q "run lock"' _ "$rc" "$out"
  # shellcheck disable=SC2086
  out=$(cd "$work/a" && RALPH_RUN_LOCK_TOKEN=wrong bash "$SB" $c 2>&1); rc=$?
  check "$c refuses with another run's token" sh -c 'test "$1" -eq 1 && printf "%s" "$2" | grep -q "run lock"' _ "$rc" "$out"
done
check "the refusals changed nothing" test "$(cd "$work/a" && git rev-parse HEAD)" = "$head0"
check "the refusals released their protocol lock" test ! -d "$(lockdir protocol)"
check "sync passes with the run's token" sh -c '(cd "$1" && RALPH_RUN_LOCK_TOKEN=$3 bash "$2" sync) 2>/dev/null' _ "$work/a" "$SB" "$tok"
check "the run lock survives its own run's sync" test "$(field run token)" = "$tok"

plant protocol busy $$
plant_tok=$tok
check "check-dupes runs while the protocol and run locks are held" sh -c '(cd "$1" && SHARED_BACKLOG_DEADLINE=5 bash "$2" check-dupes) >/dev/null 2>&1' _ "$work/a" "$SB"
check "check-dupes leaves both locks alone" test "$(field protocol token)" = busy -a "$(field run token)" = "$plant_tok"
sb unlock --force 2>/dev/null

plant run stale4 "$(dead_pid)"
check "the gate reclaims a dead run's lock" sh -c '(cd "$1" && bash "$2" sync) 2>/dev/null && test ! -d "$3"' _ "$work/a" "$SB" "$(lockdir run)"

# --- deadlines --------------------------------------------------------------

fresh
hang_origin
t0=$(date +%s)
out=$(cd "$work/a" && SHARED_BACKLOG_SSH="$work/fake-ssh" SHARED_BACKLOG_DEADLINE=2 bash "$SB" sync 2>&1); rc=$?
t1=$(date +%s)
check "sync past its deadline exits 1" test "$rc" -eq 1
check "the deadline cuts it short" test $((t1 - t0)) -lt 15
check "the expiry is reported with the state" sh -c 'printf "%s" "$1" | grep -q "deadline" && printf "%s" "$1" | grep -q "state left as is: on master"' _ "$out"
check "the killed group took the hung ssh with it" sh -c 'p=$(cat "$1"); ! kill -0 "$p" 2>/dev/null' _ "$work/ssh.pid"
check "the expired sync released its protocol lock" test ! -d "$(lockdir protocol)"

# A second command waits on the held lock, then gives up at its own deadline.
(cd "$work/a" && SHARED_BACKLOG_SSH="$work/fake-ssh" SHARED_BACKLOG_DEADLINE=6 bash "$SB" sync >/dev/null 2>&1) &
first=$!
n=0; while [ ! -f "$(lockdir protocol)/owner" ] && [ "$n" -lt 50 ]; do sleep 0.1; n=$((n + 1)); done
check "the running sync holds the protocol lock under its live pid" kill -0 "$(field protocol pid)"
held=$(field protocol token)
out=$(cd "$work/a" && SHARED_BACKLOG_DEADLINE=2 bash "$SB" sync 2>&1); rc=$?
check "a second sync gives up on the held lock" sh -c 'test "$1" -eq 1 && printf "%s" "$2" | grep -q "protocol lock is held"' _ "$rc" "$out"
check "the second sync left the first one's lock in place" test "$(field protocol token)" = "$held"
wait "$first"
check "the first sync released its lock at its deadline" test ! -d "$(lockdir protocol)"

# An expiring command leaves another owner's lock alone.
fresh
hang_origin
plant run foreign $$
out=$(cd "$work/a" && RALPH_RUN_LOCK_TOKEN=foreign SHARED_BACKLOG_SSH="$work/fake-ssh" SHARED_BACKLOG_DEADLINE=2 bash "$SB" sync 2>&1)
check "an expired command keeps the run lock it does not own" test "$(field run token)" = foreign
sb unlock --force 2>/dev/null

# check-dupes runs under the deadline too: a hung backlog doctor is killed.
mkdir -p "$work/bin"
printf '#!/bin/sh\necho $$ >"%s/doctor.pid"\nexec sleep 60\n' "$work" >"$work/bin/backlog"
chmod +x "$work/bin/backlog"
out=$(cd "$work/a" && PATH="$work/bin:$PATH" SHARED_BACKLOG_DEADLINE=2 bash "$SB" check-dupes 2>&1); rc=$?
check "check-dupes past its deadline exits 1" test "$rc" -eq 1
check "the hung backlog doctor was killed" sh -c 'p=$(cat "$1"); ! kill -0 "$p" 2>/dev/null' _ "$work/doctor.pid"
check "check-dupes created no lock" test ! -d "$(lockdir protocol)" -a ! -d "$(lockdir run)"

for bad in 0 abc -5; do
  rc=0; (cd "$work/a" && SHARED_BACKLOG_DEADLINE=$bad bash "$SB" check-dupes) >/dev/null 2>&1 || rc=$?
  check "SHARED_BACKLOG_DEADLINE=$bad is a usage error" test "$rc" -eq 64
done

echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
