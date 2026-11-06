#!/usr/bin/env bash
# Scratch-repo tests for how create of plugins/ralph/scripts/shared-backlog.sh
# reconciles an uncertain push and keeps recovery refs (TASK-308): a lost race
# reallocates with the same operation ID at most 3 times; an ambiguous push
# that origin accepted is found by its operation ID and not repeated; a failed
# reconciliation stops without allocating again and keeps the commit under
# refs/ralph/recovery/<op-id>, which survives the worktree's removal and can be
# finished as printed; a deadline or a signal mid-push also keeps the commit and
# removes the worktree. Everything runs in a `mktemp -d`: one bare repo stands
# in for origin and two clones (a, b) for two hosts. Never touches a real
# origin. Needs the backlog CLI and ps.
#
# Usage: bash tests/shell/shared-backlog-recovery-test.sh

set -u

SB="$(cd "$(dirname "$0")/../.." && pwd)/plugins/ralph/scripts/shared-backlog.sh"
work=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-recovery-test.XXXXXX")
trap 'rm -rf "$work"' EXIT

# Isolate git from the user's config (hooksPath, signing, identity, ralph.holder).
export HOME="$work/home"
export GIT_CONFIG_NOSYSTEM=1
unset RALPH_RUN_LOCK_TOKEN SHARED_BACKLOG_HOLDER SHARED_BACKLOG_DEADLINE SHARED_BACKLOG_SSH \
  GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE CLAUDE_CONFIG_DIR
mkdir -p "$HOME"
git config --global user.name tester
git config --global user.email tester@example.invalid
git config --global init.defaultBranch master

pass=0
fail=0
ok() { pass=$((pass + 1)); echo "ok   - $*"; }
nok() { fail=$((fail + 1)); echo "FAIL - $*"; }
check() { local d=$1; shift; if "$@"; then ok "$d"; else nok "$d"; fi; }
has() { case "$1" in *"$2"*) return 0 ;; esac; return 1; }

command -v backlog >/dev/null 2>&1 || { echo "backlog CLI not on PATH"; exit 1; }
command -v ps >/dev/null 2>&1 || { echo "ps not on PATH"; exit 1; }

# fresh — rebuild origin.git and the clones a and b. Origin holds TASK-1 to
# TASK-3 and x.txt. Every push from a is logged with the operation ID it
# carries, then runs $work/pre-push.sh when that exists.
fresh() {
  rm -rf "$work/origin.git" "$work/seed" "$work/a" "$work/b"
  rm -f "$work/pre-push.sh" "$work/receiving.flag"
  git init -q --bare "$work/origin.git"
  mkdir -p "$work/seed/backlog"
  printf 'task_prefix: "task"\nstatuses: ["To Do", "In Progress", "Done"]\n' >"$work/seed/backlog/config.yml"
  for d in tasks drafts completed archive/tasks docs decisions; do
    mkdir -p "$work/seed/backlog/$d"; touch "$work/seed/backlog/$d/.gitkeep"
  done
  (
    cd "$work/seed" && git init -q &&
      backlog task create "One" >/dev/null &&
      backlog task create "Two" >/dev/null &&
      backlog task create "Three" >/dev/null &&
      echo one >x.txt &&
      git add -A && git commit -q -m init &&
      git remote add origin "$work/origin.git" && git push -q origin master
  ) || { echo "seed failed"; exit 1; }
  git clone -q "$work/origin.git" "$work/a"
  git clone -q "$work/origin.git" "$work/b"
  : >"$work/pushes.log"
  cat >"$work/a/.git/hooks/pre-push" <<HOOK
#!/bin/sh
git log -1 --format='%(trailers:key=Shared-Backlog-Op,valueonly)' HEAD | grep . >>"$work/pushes.log"
[ ! -f "$work/pre-push.sh" ] || . "$work/pre-push.sh"
exit 0
HOOK
  chmod +x "$work/a/.git/hooks/pre-push"
}

in_a() { (cd "$work/a" && "$@"); }
origin_sha() { git --git-dir="$work/origin.git" rev-parse master; }
origin_ids() {
  git --git-dir="$work/origin.git" ls-tree -r --name-only master backlog/tasks |
    sed -n 's|^backlog/tasks/task-\([0-9]*\) - .*|\1|p' | sort -n | tr '\n' ' '
}
pushes() { wc -l <"$work/pushes.log" | tr -d ' '; }
op_ids() { sort -u "$work/pushes.log" | wc -l | tr -d ' '; }
op_of() { git --git-dir="$work/origin.git" log -1 --format='%(trailers:key=Shared-Backlog-Op,valueonly)' "$1" | grep .; }
worktrees() { git -C "$work/$1" worktree list --porcelain | grep -c '^worktree '; }
leftover_tmp() { ls -d "${TMPDIR:-/tmp}"/shared-backlog-create.* 2>/dev/null | grep -c . ; }
leftover_flags() { ls -d "${TMPDIR:-/tmp}"/shared-backlog-deadline.* 2>/dev/null | grep -c . ; }
# script_procs — processes still running the script under test.
script_procs() { ps -eo args= | grep -F "$SB" | grep -vc grep; }
recovery_refs() { git -C "$work/a" for-each-ref --format='%(refname)' refs/ralph/recovery; }

# kill_pusher — the body of an origin post-receive hook that kills the client's
# git push after origin has updated master: the push lands, but the client
# cannot tell.
kill_pusher='p=$PPID
while [ "$p" -gt 1 ]; do
  case "$(ps -o args= -p "$p")" in *" push "*) kill -TERM "$p"; exit 0 ;; esac
  p=$(ps -o ppid= -p "$p" | tr -d " ")
done'
post_receive() {
  printf '#!/bin/sh\n%s\n' "$1" >"$work/origin.git/hooks/post-receive"
  chmod +x "$work/origin.git/hooks/post-receive"
}

echo "# bash -n"
check "bash -n shared-backlog.sh" bash -n "$SB"
check "bash -n this suite" bash -n "$0"

echo "# a lost race reallocates in a fresh worktree with the same operation ID, at most 3 times"
fresh
# Each push from a first lets b push an unrelated commit, so a is refused.
cat >"$work/pre-push.sh" <<EOF
( unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
  cd "$work/b" && git pull -q --ff-only origin master &&
    echo sneak >>x.txt && git commit -q -am "unrelated" && git push -q origin master )
EOF
out=$(in_a bash "$SB" create "Raced" 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
check "create exits 1 (rc=$rc)" test "$rc" -eq 1
check "it pushed exactly 3 times" test "$(pushes)" -eq 3
check "all 3 pushes carried one operation ID" test "$(op_ids)" -eq 1
check "it says the push was refused 3 times" has "$out" "push refused 3 times"
check "no task landed on origin" test "$(origin_ids)" = "1 2 3 "
check "no recovery ref after definite refusals" test -z "$(recovery_refs)"
check "no temporary worktree left" test "$(worktrees a)" -eq 1

echo "# an ambiguous push that origin accepted is found by its operation ID and not repeated"
fresh
tmp_before=$(leftover_tmp)
post_receive "$kill_pusher"
before=$(origin_sha)
out=$(in_a bash "$SB" create "Ambiguous" 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
rm -f "$work/origin.git/hooks/post-receive"
op=$(head -1 "$work/pushes.log")
check "create exits 0 (rc=$rc)" test "$rc" -eq 0
check "it pushed once" test "$(pushes)" -eq 1
check "it looked for its operation ID on origin" has "$out" "looking for Shared-Backlog-Op: $op"
check "origin got exactly one new task, TASK-4" test "$(origin_ids)" = "1 2 3 4 "
check "origin's tip is the one commit pushed" test "$(git --git-dir="$work/origin.git" rev-parse master^)" = "$before"
check "origin's tip carries the operation ID" test "$(op_of master)" = "$op"
check "it reports that ID, path and SHA" has "$out" \
  "created TASK-4 $(git --git-dir="$work/origin.git" rev-parse --short master) backlog/tasks/task-4 - Ambiguous.md"
check "no recovery ref once origin is known to have it" test -z "$(recovery_refs)"
check "no temporary worktree left" test "$(worktrees a)" -eq 1
check "no temporary directory left" test "$(leftover_tmp)" -eq "$tmp_before"

echo "# a failed reconciliation stops without allocating again and keeps a recovery ref"
fresh
# The push lands, then origin goes away and the client is killed.
post_receive "( unset GIT_DIR; git -C '$work/a' remote set-url origin '$work/nowhere.git' )
$kill_pusher"
out=$(in_a bash "$SB" create "Unreconciled" 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
rm -f "$work/origin.git/hooks/post-receive"
op=$(head -1 "$work/pushes.log")
ref=refs/ralph/recovery/$op
check "create exits 2 (rc=$rc)" test "$rc" -eq 2
check "it says it does not allocate again" has "$out" "not allocating again"
check "it pushed once" test "$(pushes)" -eq 1
check "origin has the one task it accepted" test "$(origin_ids)" = "1 2 3 4 "
check "the commit is kept as $ref" test "$(recovery_refs)" = "$ref"
check "the recovery ref is origin's tip" test "$(in_a git rev-parse "$ref")" = "$(origin_sha)"
check "the recovery ref survives the worktree's removal" sh -c \
  'test "$(git -C "$1" worktree list --porcelain | grep -c "^worktree ")" -eq 1 && git -C "$1" cat-file -e "$2^{commit}"' \
  _ "$work/a" "$ref"
check "it prints how to finish the commit" has "$out" "git push origin $ref:refs/heads/master"
check "it prints how to drop the ref" has "$out" "git update-ref -d $ref"
in_a git remote set-url origin "$work/origin.git"
in_a git fetch -q origin master
check "the printed check finds it on origin" sh -c \
  'git -C "$1" log --oneline -F --grep="Shared-Backlog-Op: $2" origin/master | grep -q "task-4: add task"' _ "$work/a" "$op"
in_a git update-ref -d "$ref"
check "the printed drop removes the ref" test -z "$(recovery_refs)"

echo "# a commit that never landed can be finished from its recovery ref"
fresh
# The pre-push hook takes origin away and fails, so the push never lands and the
# reconciliation fetch fails.
cat >"$work/pre-push.sh" <<EOF
( unset GIT_DIR; git -C "$work/a" remote set-url origin "$work/nowhere.git" )
exit 1
EOF
out=$(in_a bash "$SB" create "Stranded" 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
rm -f "$work/pre-push.sh"
op=$(head -1 "$work/pushes.log")
ref=refs/ralph/recovery/$op
check "create exits 2 (rc=$rc)" test "$rc" -eq 2
check "it pushed once" test "$(pushes)" -eq 1
check "origin is unchanged" test "$(origin_ids)" = "1 2 3 "
check "the commit is kept as $ref" test "$(recovery_refs)" = "$ref"
check "no temporary worktree left" test "$(worktrees a)" -eq 1
in_a git remote set-url origin "$work/origin.git"
check "the printed finish pushes it" sh -c '(cd "$1" && git push -q origin "$2:refs/heads/master" && git update-ref -d "$2")' \
  _ "$work/a" "$ref"
check "origin now has TASK-4 with the operation ID" sh -c \
  'test "$1" = "1 2 3 4 " && test "$2" = "$3"' _ "$(origin_ids)" "$(op_of master)" "$op"

echo "# a deadline mid-push keeps a recovery ref and removes the worktree"
fresh
tmp_before=$(leftover_tmp)
post_receive "sleep 60"
start=$(date +%s)
out=$(in_a env SHARED_BACKLOG_DEADLINE=10 bash "$SB" create "Slow" 2>&1); rc=$?
took=$(($(date +%s) - start))
printf '%s\n' "$out" | sed 's/^/    /'
rm -f "$work/origin.git/hooks/post-receive"
op=$(head -1 "$work/pushes.log")
check "create exits 1 (rc=$rc)" test "$rc" -eq 1
check "it ended at the deadline (${took}s)" test "$took" -lt 30
check "it reports the deadline" has "$out" "deadline"
check "the commit is kept as refs/ralph/recovery/$op" test "$(recovery_refs)" = "refs/ralph/recovery/$op"
check "the recovery ref names the commit origin accepted" \
  test "$(in_a git rev-parse "refs/ralph/recovery/$op")" = "$(origin_sha)"
check "no temporary worktree left" test "$(worktrees a)" -eq 1
check "no temporary directory left" test "$(leftover_tmp)" -eq "$tmp_before"

echo "# a signal mid-push keeps a recovery ref and removes the worktree"
fresh
tmp_before=$(leftover_tmp)
flags_before=$(leftover_flags)
post_receive "touch '$work/receiving.flag'; sleep 60"
(cd "$work/a" && exec bash "$SB" create "Interrupted") >"$work/sig.log" 2>&1 &
pid=$!
i=0
while [ ! -f "$work/receiving.flag" ] && [ "$i" -lt 300 ]; do sleep 0.1; i=$((i + 1)); done
kill -TERM "$pid"
wait "$pid"; rc=$?
sed 's/^/    /' "$work/sig.log"
rm -f "$work/origin.git/hooks/post-receive"
op=$(head -1 "$work/pushes.log")
check "the push was under way when the signal came" test -f "$work/receiving.flag"
check "create exits 143 (rc=$rc)" test "$rc" -eq 143
check "the commit is kept as refs/ralph/recovery/$op" test "$(recovery_refs)" = "refs/ralph/recovery/$op"
check "no temporary worktree left" test "$(worktrees a)" -eq 1
check "no temporary directory left" test "$(leftover_tmp)" -eq "$tmp_before"
check "the protocol lock is released" test ! -d "$work/a/.git/shared-backlog-protocol.lock"
check "no deadline flag file left" test "$(leftover_flags)" -eq "$flags_before"
check "no watchdog or other script process left" test "$(script_procs)" -eq 0

echo
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
