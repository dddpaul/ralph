#!/usr/bin/env bash
# Scratch-repo tests for how claim, release and create of
# plugins/ralph/scripts/shared-backlog.sh retry a refused push (TASK-306): drop
# the unpushed commit, fetch, check again, recommit, push, at most 3 times, and
# never rebase. Everything runs in a `mktemp -d`: one bare repo stands in for
# origin and two clones (a, b) for two hosts. Never touches a real origin.
# Needs the backlog CLI.
#
# Usage: bash tests/shell/shared-backlog-retry-test.sh

set -u

SB="$(cd "$(dirname "$0")/../.." && pwd)/plugins/ralph/scripts/shared-backlog.sh"
work=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-retry-test.XXXXXX")
trap 'rm -rf "$work"' EXIT

# Isolate git from the user's config (hooksPath, signing, identity, ralph.holder).
export HOME="$work/home"
export GIT_CONFIG_NOSYSTEM=1
unset RALPH_RUN_LOCK_TOKEN SHARED_BACKLOG_HOLDER SHARED_BACKLOG_DEADLINE SHARED_BACKLOG_SSH \
  GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
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

# fresh — rebuild origin.git and the clones a and b. Origin holds TASK-1 to
# TASK-3, To Do, no assignee.
fresh() {
  rm -rf "$work/origin.git" "$work/seed" "$work/a" "$work/b"
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
}

in_a() { (cd "$work/a" && "$@"); }
in_b() { (cd "$work/b" && "$@"); }
origin_sha() { git --git-dir="$work/origin.git" rev-parse master; }
origin_log() { git --git-dir="$work/origin.git" log --format=%s master; }
clone_sha() { git -C "$work/$1" rev-parse HEAD; }
on_origin() { git --git-dir="$work/origin.git" merge-base --is-ancestor "$1" master 2>/dev/null; }
no_merges_on_origin() { [ -z "$(git --git-dir="$work/origin.git" rev-list --merges master)" ]; }

# who N — TASK-N's assignees on origin, space-separated.
who() {
  local p
  p=$(git --git-dir="$work/origin.git" ls-tree -r --name-only master backlog/tasks |
    grep "^backlog/tasks/task-$1 - ")
  git --git-dir="$work/origin.git" show "master:$p" |
    awk 'NR > 1 && /^---$/ { exit } inl && /^ +- / { v = $0; sub(/^ +- +/, "", v); gsub(/\047/, "", v); o = o v " "; next }
         inl { exit } /^assignee:/ { inl = 1 } END { sub(/ $/, "", o); print o }'
}

# origin_ids — task IDs on origin's master, space-separated.
origin_ids() {
  git --git-dir="$work/origin.git" ls-tree -r --name-only master backlog/tasks |
    sed -n 's|^backlog/tasks/task-\([0-9]*\) - .*|\1|p' | sort -n | tr '\n' ' '
}

# Server-side delay so two pushes started together both pass sync before
# either lands: a real race, decided by the server's ref update.
slow_origin() {
  printf '#!/bin/sh\nsleep 2\n' >"$work/origin.git/hooks/pre-receive"
  chmod +x "$work/origin.git/hooks/pre-receive"
}
fast_origin() { rm -f "$work/origin.git/hooks/pre-receive"; }

# sneak_hook LIMIT — a pre-push hook in clone a that, on each of its first
# LIMIT runs, lands an unrelated commit on origin from clone b, so a's push
# arrives behind origin and is refused. Counts its runs in $work/sneaks.
sneak_hook() {
  : >"$work/sneaks"
  cat >"$work/a/.git/hooks/pre-push" <<EOF
#!/bin/sh
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
n=\$(wc -l <"$work/sneaks")
[ "\$n" -lt $1 ] || exit 0
echo x >>"$work/sneaks"
cd "$work/b" && git pull -q --ff-only origin master &&
  echo "\$n" >>x.txt && git commit -q -am "unrelated \$n" && git push -q origin master
EOF
  chmod +x "$work/a/.git/hooks/pre-push"
}
sneaks() { wc -l <"$work/sneaks" | tr -d ' '; }

echo "# no rebase in the protocol"
check "no git rebase in shared-backlog.sh" sh -c '! grep -n "git rebase" "$1"' _ "$SB"
check "bash -n shared-backlog.sh" bash -n "$SB"

echo "# two clones race to claim one task"
fresh
slow_origin
in_a bash "$SB" claim 1 --as @host-a >"$work/a.out" 2>&1 & pa=$!
in_b bash "$SB" claim 1 --as @host-b >"$work/b.out" 2>&1 & pb=$!
wait "$pa"; ra=$?
wait "$pb"; rb=$?
fast_origin
sed 's/^/    /' "$work/a.out" "$work/b.out"
check "exactly one claim exits 0 (a=$ra b=$rb)" test $(( (ra == 0) + (rb == 0) )) -eq 1
if [ "$ra" -eq 0 ]; then winner=@host-a; loser=b; else winner=@host-b; loser=a; fi
check "the loser exits 1" test $(( ra + rb )) -eq 1
check "origin's assignee is the winner" test "$(who 1)" = "$winner"
check "exactly one claim commit on origin" test "$(origin_log | grep -c 'claim for')" -eq 1
check "the loser reports the winner" grep -q "TASK-1 taken by $winner" "$work/$loser.out"
check "the loser's master equals origin" test "$(clone_sha "$loser")" = "$(origin_sha)"
check "the loser's tree is clean" test -z "$(in_$loser git status --porcelain --untracked-files=no)"
check "origin's history has no merges" no_merges_on_origin

echo "# a release racing a claim"
fresh
in_a bash "$SB" claim 1 --as @host-a >/dev/null 2>&1
in_b bash "$SB" sync 2>/dev/null
slow_origin
in_a bash "$SB" release 1 --as @host-a >"$work/a.out" 2>&1 & pa=$!
in_b bash "$SB" claim 2 --as @host-b >"$work/b.out" 2>&1 & pb=$!
wait "$pa"; ra=$?
wait "$pb"; rb=$?
fast_origin
sed 's/^/    /' "$work/a.out" "$work/b.out"
check "the release and the claim both exit 0 (a=$ra b=$rb)" test "$ra" -eq 0 -a "$rb" -eq 0
check "one push was refused and retried" sh -c 'cat "$1" "$2" | grep -q rejected' _ "$work/a.out" "$work/b.out"
check "origin's TASK-1 has no assignee" test -z "$(who 1)"
check "origin's TASK-2 is held by @host-b" test "$(who 2)" = @host-b
check "both commits are on origin" sh -c 'origin_log() { git --git-dir="$1" log --format=%s master; }
  origin_log "$1" | grep -q "task-1: release from @host-a" && origin_log "$1" | grep -q "task-2: claim for @host-b"' _ "$work/origin.git"
check "origin's history has no merges" no_merges_on_origin
check "clone a carries nothing origin lacks" on_origin "$(clone_sha a)"
check "clone b carries nothing origin lacks" on_origin "$(clone_sha b)"

echo "# a claim retries after an unrelated commit lands on origin"
fresh
sneak_hook 1
out=$(in_a bash "$SB" claim 3 --as @host-a 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
check "the claim exits 0 (rc=$rc)" test "$rc" -eq 0
check "the first push was refused once" test "$(sneaks)" -eq 1
check "origin's TASK-3 is held by @host-a" test "$(who 3)" = @host-a
check "the claim is a fresh commit on top of the unrelated one" \
  test "$(origin_log | head -2 | tr '\n' '|')" = "task-3: claim for @host-a|unrelated 0|"
check "clone a's master equals origin" test "$(clone_sha a)" = "$(origin_sha)"
check "origin's history has no merges" no_merges_on_origin

echo "# a release retries after an unrelated commit lands on origin"
sneak_hook 1
out=$(in_a bash "$SB" release 3 --as @host-a 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
check "the release exits 0 (rc=$rc)" test "$rc" -eq 0
check "origin's TASK-3 has no assignee" test -z "$(who 3)"
check "the release is a fresh commit on top of the unrelated one" \
  test "$(origin_log | head -2 | tr '\n' '|')" = "task-3: release from @host-a|unrelated 0|"
check "clone a's master equals origin" test "$(clone_sha a)" = "$(origin_sha)"

echo "# a claim refused on every push gives up after 3 tries"
fresh
sneak_hook 99
out=$(in_a bash "$SB" claim 3 --as @host-a 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
check "the claim exits 1 (rc=$rc)" test "$rc" -eq 1
check "it pushed exactly 3 times" test "$(sneaks)" -eq 3
check "it says the push was refused 3 times" has "$out" "push refused 3 times"
check "no claim landed on origin" sh -c '! git --git-dir="$1" log --format=%s master | grep -q "claim for"' _ "$work/origin.git"
check "clone a's master equals origin" test "$(clone_sha a)" = "$(origin_sha)"
check "clone a's tree is clean" test -z "$(in_a git status --porcelain --untracked-files=no)"

echo "# two clones race to create a task"
fresh
slow_origin
in_a bash "$SB" create "Alpha" >"$work/a.out" 2>&1 & pa=$!
in_b bash "$SB" create "Beta" >"$work/b.out" 2>&1 & pb=$!
wait "$pa"; ra=$?
wait "$pb"; rb=$?
fast_origin
sed 's/^/    /' "$work/a.out" "$work/b.out"
check "both creates exit 0 (a=$ra b=$rb)" test "$ra" -eq 0 -a "$rb" -eq 0
check "origin has TASK-1 to TASK-5 once each" test "$(origin_ids)" = "1 2 3 4 5 "
check "origin's tip commit is 'task-5: add task'" test "$(origin_log | head -1)" = "task-5: add task"
check "origin's history has no merges" no_merges_on_origin

echo
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
