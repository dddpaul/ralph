#!/usr/bin/env bash
# Scratch-repo tests for scripts/shared-backlog.sh and scripts/hooks/pre-push.
# Everything runs in a `mktemp -d`: one bare repo stands in for origin and two
# clones (a, b) stand in for two hosts. Never touches a real origin.
#
# Usage: bash scripts/tests/shared-backlog-test.sh

set -u

src=$(cd "$(dirname "$0")/../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-test.XXXXXX")
trap 'rm -rf "$work"' EXIT

# Isolate git from the user's config (hooksPath, signing, identity).
export HOME="$work/home"
export GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME"
git config --global user.name tester
git config --global user.email tester@example.invalid
git config --global init.defaultBranch master
git config --global advice.detachedHead false

pass=0
fail=0
ok() { pass=$((pass + 1)); echo "ok   - $*"; }
nok() { fail=$((fail + 1)); echo "FAIL - $*"; }
check() { local d=$1; shift; if "$@"; then ok "$d"; else nok "$d"; fi; }

SB="scripts/shared-backlog.sh"
UNREACHABLE="ssh://192.0.2.1/nowhere.git"   # TEST-NET-1, never routed

# fresh — rebuild origin.git and clones a, b; origin holds TASK-1 (To Do).
fresh() {
  rm -rf "$work/origin.git" "$work/seed" "$work/a" "$work/b" "$work/check"
  git init -q --bare "$work/origin.git"
  mkdir -p "$work/seed/backlog" "$work/seed/scripts/hooks"
  cp "$src/backlog/config.yml" "$work/seed/backlog/"
  for d in tasks drafts completed archive/tasks docs decisions; do
    mkdir -p "$work/seed/backlog/$d"; touch "$work/seed/backlog/$d/.gitkeep"
  done
  cp "$src/scripts/shared-backlog.sh" "$work/seed/scripts/"
  cp "$src/scripts/hooks/pre-push" "$work/seed/scripts/hooks/"
  echo one >"$work/seed/x.txt"; echo one >"$work/seed/y.txt"
  (cd "$work/seed" && git init -q && backlog task create "First task" >/dev/null &&
    git add -A && git commit -q -m init &&
    git remote add origin "$work/origin.git" && git push -q origin master) ||
    { echo "seed failed"; exit 1; }
  for c in a b; do
    git clone -q "$work/origin.git" "$work/$c"
    (cd "$work/$c" && bash "$SB" install-hooks >/dev/null)
  done
}

in_a() { (cd "$work/a" && "$@"); }
in_b() { (cd "$work/b" && "$@"); }
origin_sha() { git --git-dir="$work/origin.git" rev-parse master; }

# origin_ids — task IDs on origin's master, one per line.
origin_ids() {
  git --git-dir="$work/origin.git" ls-tree -r --name-only master backlog/tasks |
    sed -n 's|^backlog/tasks/task-\([0-9]*\) - .*|\1|p' | sort -n
}

# origin_never_had_dupes — every commit origin's master ever pointed at is
# free of duplicate IDs (so no duplicate landed even briefly).
origin_never_had_dupes() {
  local c
  for c in $(git --git-dir="$work/origin.git" rev-list master); do
    git --git-dir="$work/origin.git" ls-tree -r --name-only "$c" backlog/tasks |
      sed -n 's|^backlog/tasks/task-\([0-9]*\) - .*|\1|p' | sort | uniq -d | grep -q . &&
      return 1
  done
  return 0
}

fresh_clone_doctor() {
  rm -rf "$work/check"
  git clone -q "$work/origin.git" "$work/check" && (cd "$work/check" && backlog doctor >/dev/null 2>&1)
}

# Server-side delay so two pushes started together both pass sync before
# either lands: a real race, decided by the server's ref update.
slow_origin() {
  printf '#!/bin/sh\nsleep 2\n' >"$work/origin.git/hooks/pre-receive"
  chmod +x "$work/origin.git/hooks/pre-receive"
}
fast_origin() { rm -f "$work/origin.git/hooks/pre-receive"; }

echo "# bash -n"
check "bash -n scripts/shared-backlog.sh" bash -n "$src/scripts/shared-backlog.sh"
check "bash -n scripts/hooks/pre-push" bash -n "$src/scripts/hooks/pre-push"
for sub in sync claim release create integrate check-dupes renumber install-hooks; do
  check "subcommand '$sub' is dispatched" grep -q "^  $sub) cmd_" "$src/scripts/shared-backlog.sh"
done

echo "# claim race"
fresh
slow_origin
in_a bash "$SB" claim 1 --as @host-a >"$work/a.out" 2>&1 & pa=$!
in_b bash "$SB" claim 1 --as @host-b >"$work/b.out" 2>&1 & pb=$!
wait "$pa"; ra=$?
wait "$pb"; rb=$?
fast_origin
cat "$work/a.out" "$work/b.out" | sed 's/^/    /'
check "exactly one claim exits 0 (a=$ra b=$rb)" [ $(( (ra == 0) + (rb == 0) )) -eq 1 ]
if [ "$ra" -eq 0 ]; then winner=@host-a; loser_out="$work/b.out"; else winner=@host-b; loser_out="$work/a.out"; fi
owner=$(git --git-dir="$work/origin.git" show "master:backlog/tasks/task-1 - First-task.md" |
  sed -n "s/^  - '\(@[^']*\)'$/\1/p")
check "origin's assignee is the winner ($owner)" [ "$owner" = "$winner" ]
check "the loser names the holder" grep -q "TASK-1 taken by $winner" "$loser_out"
check "exactly one claim commit on origin" \
  [ "$(git --git-dir="$work/origin.git" log --oneline master | grep -c 'claim for')" -eq 1 ]
in_a git merge-base --is-ancestor HEAD "$(origin_sha)"
check "clone a is at or behind origin (no stray claim)" [ $? -eq 0 ]
in_b git merge-base --is-ancestor HEAD "$(origin_sha)"
check "clone b is at or behind origin (no stray claim)" [ $? -eq 0 ]

echo "# claim of a task already claimed on origin"
in_b bash "$SB" sync 2>/dev/null
out=$(in_b bash "$SB" claim 1 --as @host-c 2>&1); rc=$?
check "a late claim exits non-zero naming the holder" [ "$rc" -ne 0 ]
case "$out" in *"taken by $winner"*) ok "late claim message: $out" ;; *) nok "late claim message: $out" ;; esac

echo "# claim leaves To Do with the holder as assignee"
view=$(cd "$work/check" 2>/dev/null || fresh_clone_doctor; cd "$work/check" && git pull -q && backlog task view 1 --plain)
check "view shows Status To Do" grep -q '^Status: .*To Do$' <<EOF
$view
EOF
check "view shows Assignee $winner" grep -q "^Assignee: $winner\$" <<EOF
$view
EOF

echo "# release"
if [ "$winner" = @host-a ]; then wc=a; else wc=b; fi
out=$( (cd "$work/$wc" && bash "$SB" release 1 --as "$winner") 2>&1); rc=$?
check "release by the holder exits 0 ($out)" [ "$rc" -eq 0 ]
check "origin's TASK-1 has no assignee after release" \
  git --git-dir="$work/origin.git" grep -q '^assignee: \[\]$' master -- "backlog/tasks/task-1 - First-task.md"

echo "# create race: both clones create at once (push refused, rebase, renumber)"
fresh
slow_origin
in_a bash "$SB" create "Alpha" >"$work/a.out" 2>&1 & pa=$!
in_b bash "$SB" create "Beta" >"$work/b.out" 2>&1 & pb=$!
wait "$pa"; ra=$?
wait "$pb"; rb=$?
fast_origin
cat "$work/a.out" "$work/b.out" | sed 's/^/    /'
check "both creates exit 0 (a=$ra b=$rb)" [ "$ra" -eq 0 ] && [ "$rb" -eq 0 ]
check "origin has TASK-1, 2 and 3" [ "$(origin_ids | tr '\n' ' ')" = "1 2 3 " ]
check "origin's tip commit is 'task-3: add task'" sh -c \
  "git --git-dir='$work/origin.git' log -1 --format=%s master | grep -qx 'task-3: add task'"
check "origin never carried a duplicate ID" origin_never_had_dupes
check "backlog doctor exits 0 on a fresh clone" fresh_clone_doctor

echo "# stale clone behind: origin already has TASK-2, b never saw it"
fresh
in_a bash "$SB" create "Alpha" >/dev/null 2>&1
in_b git remote set-url origin "$UNREACHABLE"
out=$(in_b bash "$SB" create "Beta" 2>&1)
check "b creates a provisional TASK-2 offline ($out)" grep -q 'created TASK-2, provisional' <<EOF
$out
EOF
in_b git remote set-url origin "$work/origin.git"
out=$(in_b bash "$SB" integrate 2>&1); rc=$?
echo "$out" | sed 's/^/    /'
check "integrate exits 0" [ "$rc" -eq 0 ]
check "b's copy was renumbered to TASK-3" grep -q 'renumbered TASK-2 -> TASK-3' <<EOF
$out
EOF
check "origin's TASK-2 is still a's Alpha" \
  git --git-dir="$work/origin.git" cat-file -e "master:backlog/tasks/task-2 - Alpha.md"
check "origin's TASK-3 is b's Beta" \
  git --git-dir="$work/origin.git" cat-file -e "master:backlog/tasks/task-3 - Beta.md"
check "TASK-3's frontmatter id is TASK-3" \
  git --git-dir="$work/origin.git" grep -q '^id: TASK-3$' master -- "backlog/tasks/task-3 - Beta.md"
check "origin never carried a duplicate ID" origin_never_had_dupes
check "backlog doctor exits 0 on a fresh clone" fresh_clone_doctor

echo "# stale clone ahead: b's unpushed TASK-2 is older than a's pushed TASK-2"
fresh
in_b git remote set-url origin "$UNREACHABLE"
in_b bash "$SB" create "Beta" >/dev/null 2>&1
sleep 1
in_a bash "$SB" create "Alpha" >/dev/null 2>&1
in_b git remote set-url origin "$work/origin.git"
out=$(in_b bash "$SB" integrate 2>&1); rc=$?
echo "$out" | sed 's/^/    /'
check "integrate exits 0" [ "$rc" -eq 0 ]
check "b's (older) copy was renumbered, a's pushed copy kept TASK-2" \
  git --git-dir="$work/origin.git" cat-file -e "master:backlog/tasks/task-2 - Alpha.md"
check "origin's TASK-3 is b's Beta" \
  git --git-dir="$work/origin.git" cat-file -e "master:backlog/tasks/task-3 - Beta.md"
check "origin never carried a duplicate ID" origin_never_had_dupes
check "backlog doctor exits 0 on a fresh clone" fresh_clone_doctor

echo "# pre-push hook refuses a duplicate ID"
fresh
before=$(origin_sha)
in_a cp "backlog/tasks/task-1 - First-task.md" "backlog/tasks/task-1 - Copy.md"
in_a git add -A
in_a git commit -q -m "add a duplicate"
out=$(in_a git push origin master 2>&1); rc=$?
echo "$out" | sed 's/^/    /'
check "plain git push exits non-zero" [ "$rc" -ne 0 ]
check "the hook names the duplicate" grep -q 'duplicate task IDs' <<EOF
$out
EOF
check "origin is unchanged" [ "$(origin_sha)" = "$before" ]
out=$(in_a bash "$SB" check-dupes 2>&1); rc=$?
check "check-dupes exits 1 on the same tree" [ "$rc" -eq 1 ]
out=$(in_a bash "$SB" renumber 2>&1)
check "renumber moves the unpushed copy to TASK-2" grep -q 'renumbered TASK-1 -> TASK-2 (backlog/tasks/task-2 - Copy.md)' <<EOF
$out
EOF
out=$(in_a git push -q origin master 2>&1); rc=$?
check "after renumber the push passes the hook" [ "$rc" -eq 0 ]
check "backlog doctor exits 0 on a fresh clone" fresh_clone_doctor

echo "# integrate: diverged master, separate files"
fresh
in_a sh -c 'echo two >x.txt && git commit -qam "a: x" && git push -q origin master'
in_b sh -c 'printf "#!/bin/sh\necho hi\n" >tool.sh && git add tool.sh && git commit -qm "b: tool"'
out=$(in_b bash "$SB" integrate --task 7 2>&1); rc=$?
echo "$out" | sed 's/^/    /'
check "integrate exits 0" [ "$rc" -eq 0 ]
check "origin has both changes" sh -c \
  "git --git-dir='$work/origin.git' show master:x.txt | grep -q two && git --git-dir='$work/origin.git' cat-file -e master:tool.sh"
check "origin's tip is a task-7 merge commit" sh -c \
  "git --git-dir='$work/origin.git' log -1 --format=%s master | grep -q '^task-7: merge origin/master'"
fresh
in_a sh -c 'echo two >x.txt && git commit -qam "a: x" && git push -q origin master'
in_b sh -c 'echo three >y.txt && git commit -qam "b: y"'
out=$(cd "$work/b" && SHARED_BACKLOG_CHECKS="touch '$work/checks-ran'" bash "$SB" integrate 2>&1); rc=$?
check "integrate reruns the checks on the merged tree" [ -f "$work/checks-ran" ]
check "and pushes (rc=$rc)" [ "$(origin_sha)" = "$(in_b git rev-parse HEAD)" ]
fresh
in_a sh -c 'echo two >x.txt && git commit -qam "a: x" && git push -q origin master'
in_b sh -c 'echo three >y.txt && git commit -qam "b: y"'
before=$(origin_sha)
out=$(cd "$work/b" && SHARED_BACKLOG_CHECKS=false bash "$SB" integrate 2>&1); rc=$?
check "failing checks: integrate exits non-zero" [ "$rc" -ne 0 ]
check "failing checks: origin is unchanged" [ "$(origin_sha)" = "$before" ]

fresh
in_a sh -c 'echo two >x.txt && git commit -qam "a: x" && git push -q origin master'
in_b sh -c 'printf "if then\n" >broken.sh && git add broken.sh && git commit -qm "b: broken"'
before=$(origin_sha)
out=$(in_b bash "$SB" integrate 2>&1); rc=$?
check "default checks: a touched .sh failing bash -n blocks the push (rc=$rc)" [ "$rc" -ne 0 ]
check "default checks: origin is unchanged" [ "$(origin_sha)" = "$before" ]

echo "# integrate: merge that cannot start"
fresh
in_a sh -c 'echo new >z.txt && git add z.txt && git commit -qm "a: z" && git push -q origin master'
in_b sh -c 'echo three >y.txt && git commit -qam "b: y" && echo local >z.txt'
before=$(origin_sha)
out=$(in_b bash "$SB" integrate 2>&1); rc=$?
echo "$out" | sed 's/^/    /'
check "untracked file in the way: integrate exits 1 (rc=$rc)" [ "$rc" -eq 1 ]
check "and shows git's reason" grep -q 'would be overwritten' <<EOF
$out
EOF
check "and origin is unchanged" [ "$(origin_sha)" = "$before" ]

echo "# claim and create refuse while local master is ahead of origin"
fresh
in_b sh -c 'echo work >work.txt && git add work.txt && git commit -qm "b: unpushed work"'
b_before=$(in_b git rev-parse HEAD)
before=$(origin_sha)
out=$(in_b bash "$SB" claim 1 --as @host-b 2>&1); rc=$?
check "claim with unpushed work exits non-zero (rc=$rc)" [ "$rc" -ne 0 ]
check "and says to integrate first" grep -q 'ahead of origin/master; run integrate first' <<EOF
$out
EOF
check "and keeps the unpushed work" [ "$(in_b git rev-parse HEAD)" = "$b_before" ]
out=$(in_b bash "$SB" create "Gamma" 2>&1); rc=$?
check "create with unpushed work exits non-zero (rc=$rc)" [ "$rc" -ne 0 ]
check "and creates nothing" [ "$(in_b git rev-parse HEAD)" = "$b_before" ]
check "origin is unchanged" [ "$(origin_sha)" = "$before" ]

echo "# integrate: real conflict"
fresh
in_a sh -c 'echo two >x.txt && git commit -qam "a: x" && git push -q origin master'
in_b sh -c 'echo three >x.txt && git commit -qam "b: x"'
before=$(origin_sha)
b_before=$(in_b git rev-parse HEAD)
out=$(in_b bash "$SB" integrate 2>&1); rc=$?
echo "$out" | sed 's/^/    /'
check "integrate exits non-zero" [ "$rc" -ne 0 ]
check "origin is unchanged" [ "$(origin_sha)" = "$before" ]
check "b's master is unchanged and the merge aborted" sh -c \
  "[ \"\$(cd '$work/b' && git rev-parse HEAD)\" = '$b_before' ] && [ ! -e '$work/b/.git/MERGE_HEAD' ]"

echo "# unreachable origin"
fresh
in_b git remote set-url origin "$UNREACHABLE"
t0=$(date +%s)
out=$(in_b bash "$SB" sync </dev/null 2>&1); rc=$?
t1=$(date +%s)
echo "$out" | sed 's/^/    /'
check "sync exits 2 (unreachable), rc=$rc" [ "$rc" -eq 2 ]
check "sync returns within 10 s ($((t1 - t0)) s)" [ $((t1 - t0)) -le 10 ]
out=$(in_b bash "$SB" create "Offline task" </dev/null 2>&1); rc=$?
echo "$out" | sed 's/^/    /'
check "create still creates the task (rc=$rc)" in_b test -f "backlog/tasks/task-2 - Offline-task.md"
check "and commits it locally" sh -c "cd '$work/b' && git log -1 --format=%s | grep -q '^task-2: add task'"
out=$(in_b bash "$SB" claim 1 --as @host-b </dev/null 2>&1); rc=$?
check "claim refuses while origin is unreachable (rc=$rc)" [ "$rc" -eq 2 ]

echo "# install-hooks"
check "pre-push is installed in clone a" grep -q 'shared-backlog pre-push hook' "$work/a/.git/hooks/pre-push"
echo '#!/bin/sh' >"$work/a/.git/hooks/pre-push"
out=$(in_a bash "$SB" install-hooks 2>&1); rc=$?
check "install-hooks refuses to overwrite a foreign hook" [ "$rc" -ne 0 ]

echo
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
