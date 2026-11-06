#!/usr/bin/env bash
# Scratch-repo tests for integrate in plugins/ralph/scripts/shared-backlog.sh
# (TASK-309): it merges origin/master, never rebases, and writes an
# Integrated-Origin trailer; it takes its opt-in and checks from the HEAD before
# the merge; it fails before merging without checks or their context; it stops
# on duplicate IDs with an old-to-new mapping and neither pushes nor renumbers;
# it leaves an interrupted merge as it is; it retries a push only when it was
# not a fast-forward. Everything runs in a `mktemp -d`: one bare repo stands in
# for origin and two clones (a, b) for two hosts. Never touches a real origin.
# Needs the backlog CLI and jq.
#
# Usage: bash tests/shell/shared-backlog-integrate-test.sh

set -u

SB="$(cd "$(dirname "$0")/../.." && pwd)/plugins/ralph/scripts/shared-backlog.sh"
work=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-integrate-test.XXXXXX")
trap 'rm -rf "$work"' EXIT

# Isolate git from the user's config (hooksPath, signing, identity, ralph.holder).
export HOME="$work/home"
export GIT_CONFIG_NOSYSTEM=1
unset RALPH_RUN_LOCK_TOKEN SHARED_BACKLOG_HOLDER SHARED_BACKLOG_DEADLINE SHARED_BACKLOG_SSH \
  SHARED_BACKLOG_CHECKS SHARED_BACKLOG_CHECKS_EXEC GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
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
command -v jq >/dev/null 2>&1 || { echo "jq not on PATH"; exit 1; }

# marker CHECKS — an opted-in .claude/ralph.json whose checks run CHECKS.
marker() { jq -n --arg c "$1" '{sharedBacklog: true, checks: $c}'; }

# fresh [MARKER] — rebuild origin.git and the clones a and b. Origin holds
# TASK-1 to TASK-3 and, unless MARKER is "none", an opted-in marker whose
# checks log to $work/checks.log.
fresh() {
  rm -rf "$work/origin.git" "$work/seed" "$work/a" "$work/b" "$work/checks.log"
  git init -q --bare "$work/origin.git"
  mkdir -p "$work/seed/backlog" "$work/seed/.claude"
  printf 'task_prefix: "task"\nstatuses: ["To Do", "In Progress", "Done"]\n' >"$work/seed/backlog/config.yml"
  for d in tasks drafts completed archive/tasks docs decisions; do
    mkdir -p "$work/seed/backlog/$d"; touch "$work/seed/backlog/$d/.gitkeep"
  done
  [ "${1:-}" = none ] || marker "echo checks >>'$work/checks.log'" >"$work/seed/.claude/ralph.json"
  (
    cd "$work/seed" && git init -q &&
      backlog task create "One" >/dev/null &&
      backlog task create "Two" >/dev/null &&
      backlog task create "Three" >/dev/null &&
      echo one >x.txt && echo one >y.txt &&
      git add -A && git commit -q -m init &&
      git remote add origin "$work/origin.git" && git push -q origin master
  ) || { echo "seed failed"; exit 1; }
  git clone -q "$work/origin.git" "$work/a"
  git clone -q "$work/origin.git" "$work/b"
}

in_a() { (cd "$work/a" && "$@"); }
in_b() { (cd "$work/b" && "$@"); }
origin_sha() { git --git-dir="$work/origin.git" rev-parse master; }
clone_sha() { git -C "$work/$1" rev-parse HEAD; }
on_origin() { git --git-dir="$work/origin.git" merge-base --is-ancestor "$1" master 2>/dev/null; }
checks_ran() { [ -f "$work/checks.log" ]; }

# diverge — an unrelated commit on origin from b, and one in a's master.
diverge() {
  in_b sh -c 'echo b >>x.txt && git commit -q -am "b work" && git push -q origin master'
  in_a sh -c 'echo a >>y.txt && git commit -q -am "a work"'
}

# integrate_a [ENV=VALUE...] — run integrate in clone a; sets out and rc.
integrate_a() {
  out=$(cd "$work/a" && env "$@" bash "$SB" integrate 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    /'
}

# not_merged — clone a's HEAD is still HEAD0 and no merge is in progress.
not_merged() {
  [ "$(clone_sha a)" = "$head0" ] && [ ! -f "$work/a/.git/MERGE_HEAD" ] && [ "$(origin_sha)" = "$origin0" ]
}

# sneak_hook LIMIT — a pre-push hook in clone a that, on each of its first
# LIMIT runs, lands an unrelated commit on origin from clone b, so a's push
# arrives behind origin and is refused. Counts its runs in $work/pushes.
sneak_hook() {
  : >"$work/pushes"
  cat >"$work/a/.git/hooks/pre-push" <<EOF
#!/bin/sh
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
echo x >>"$work/pushes"
n=\$(wc -l <"$work/pushes")
[ "\$n" -le $1 ] || exit 0
cd "$work/b" && git pull -q --ff-only origin master &&
  echo "\$n" >>x.txt && git commit -q -am "unrelated \$n" && git push -q origin master
EOF
  chmod +x "$work/a/.git/hooks/pre-push"
}
pushes() { wc -l <"$work/pushes" | tr -d ' '; }

echo "# no rebase"
check "no git rebase in shared-backlog.sh" sh -c '! grep -n "git rebase" "$1"' _ "$SB"
check "no renumber --amend left" sh -c '! grep -n -- "--amend" "$1"' _ "$SB"

echo "# a diverged master is merged with an Integrated-Origin trailer"
fresh
diverge
before=$(clone_sha a)
fetched=$(origin_sha)
integrate_a
check "integrate exits 0 (rc=$rc)" test "$rc" -eq 0
check "origin's tip is a's HEAD" test "$(origin_sha)" = "$(clone_sha a)"
check "the tip is a merge" test "$(git -C "$work/a" rev-list --parents -n1 HEAD | wc -w | tr -d ' ')" -eq 3
check "its first parent is a's own master" test "$(git -C "$work/a" rev-parse HEAD^1)" = "$before"
check "its second parent is the fetched origin SHA" test "$(git -C "$work/a" rev-parse HEAD^2)" = "$fetched"
trailer=$(git -C "$work/a" log -1 --format='%(trailers:key=Integrated-Origin,valueonly)' | tr -d '\n')
check "its Integrated-Origin trailer names the fetched origin SHA" test "$trailer" = "$fetched"
check "the configured checks ran" checks_ran

echo "# integrate --task N names the task in the merge subject"
fresh
diverge
out=$(cd "$work/a" && bash "$SB" integrate --task 7 2>&1); rc=$?
check "integrate --task 7 exits 0 (rc=$rc)" test "$rc" -eq 0
check "the subject is 'task-7: merge origin/master'" \
  test "$(git -C "$work/a" log -1 --format=%s)" = "task-7: merge origin/master"

echo "# a master only ahead of origin is pushed without a merge"
fresh
in_a sh -c 'echo a >>y.txt && git commit -q -am "a work"'
integrate_a
check "integrate exits 0 (rc=$rc)" test "$rc" -eq 0
check "origin has a's commit" test "$(origin_sha)" = "$(clone_sha a)"
check "no merge commit was made" test -z "$(git -C "$work/a" rev-list --merges HEAD)"

echo "# policy: no marker in HEAD fails before merging"
fresh none
diverge
head0=$(clone_sha a); origin0=$(origin_sha)
integrate_a
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it says the clone is not opted in" has "$out" "not opted in"
check "nothing merged or pushed" not_merged

echo "# policy: a marker without sharedBacklog true fails before merging"
fresh none
mkdir -p "$work/a/.claude"
printf '{"sharedBacklog": false, "checks": "true"}\n' >"$work/a/.claude/ralph.json"
in_a sh -c 'git add .claude/ralph.json && git commit -q -m "marker off"'
diverge
head0=$(clone_sha a); origin0=$(origin_sha)
integrate_a
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it says sharedBacklog is not true" has "$out" '"sharedBacklog": true'
check "nothing merged or pushed" not_merged

echo "# policy: no checks configured fails before merging"
fresh
printf '{"sharedBacklog": true}\n' >"$work/a/.claude/ralph.json"
in_a sh -c 'git commit -q -am "no checks"'
diverge
head0=$(clone_sha a); origin0=$(origin_sha)
integrate_a
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it says no checks are configured" has "$out" "no checks configured"
check "nothing merged or pushed" not_merged
integrate_a SHARED_BACKLOG_CHECKS="echo env >>'$work/checks.log'"
check "SHARED_BACKLOG_CHECKS supplies the checks (rc=$rc)" test "$rc" -eq 0
check "the env checks ran" grep -qx env "$work/checks.log"

echo "# policy: a missing execution context fails before merging"
fresh
diverge
head0=$(clone_sha a); origin0=$(origin_sha)
integrate_a SHARED_BACKLOG_CHECKS_EXEC="$work/no-such-container exec"
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it says the execution context is missing" has "$out" "execution context is missing"
check "nothing merged or pushed" not_merged
check "the checks did not run" sh -c '! test -f "$1"' _ "$work/checks.log"
printf '#!/bin/sh\necho "in-context $*" >>"%s"\nexec "$@"\n' "$work/ctx.log" >"$work/ctx"
chmod +x "$work/ctx"
integrate_a SHARED_BACKLOG_CHECKS_EXEC="$work/ctx"
check "with a working context integrate exits 0 (rc=$rc)" test "$rc" -eq 0
check "the checks ran through the context prefix" grep -q "in-context sh -c echo checks" "$work/ctx.log"

echo "# policy: a merged-in commit that changes checks does not change them"
fresh
marker "echo new >>'$work/checks.log'" >"$work/b/.claude/ralph.json"
in_b sh -c 'git commit -q -am "change checks" && git push -q origin master'
in_a sh -c 'echo a >>y.txt && git commit -q -am "a work"'
integrate_a
check "integrate exits 0 (rc=$rc)" test "$rc" -eq 0
check "the merged tree carries the new checks" has "$(cat "$work/a/.claude/ralph.json")" "echo new"
check "the pre-merge HEAD's checks ran" grep -qx checks "$work/checks.log"
check "the merged-in checks did not run" sh -c '! grep -qx new "$1"' _ "$work/checks.log"

echo "# policy: a merged-in commit that removes the marker does not opt out"
fresh
in_b sh -c 'git rm -q .claude/ralph.json && git commit -q -m "drop marker" && git push -q origin master'
in_a sh -c 'echo a >>y.txt && git commit -q -am "a work"'
integrate_a
check "integrate exits 0 (rc=$rc)" test "$rc" -eq 0
check "the merged tree has no marker" test ! -f "$work/a/.claude/ralph.json"
check "the pre-merge HEAD's checks ran" grep -qx checks "$work/checks.log"
check "origin has a's merge" test "$(origin_sha)" = "$(clone_sha a)"

echo "# a failing check stops before the push"
fresh
diverge
origin0=$(origin_sha)
integrate_a SHARED_BACKLOG_CHECKS=false
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it says the checks failed" has "$out" "checks failed"
check "origin unchanged" test "$(origin_sha)" = "$origin0"

echo "# duplicate IDs stop with an old-to-new mapping, no push, no renumber"
fresh
# a takes TASK-4 first, unpushed, so that backlog's look at origin cannot
# steer b away from the same ID.
in_a sh -c 'backlog task create "Mine" >/dev/null && git add -A && git commit -q -m "task-4: add Mine"'
in_b sh -c 'backlog task create "Theirs" >/dev/null && git add -A && git commit -q -m "task-4: add Theirs" && git push -q origin master'
origin0=$(origin_sha)
integrate_a
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it maps TASK-4 to TASK-5" has "$out" "TASK-4 -> TASK-5  backlog/tasks/task-4 - Mine.md"
check "it names the copy that keeps TASK-4" has "$out" "task-4 - Theirs.md"
check "origin unchanged" test "$(origin_sha)" = "$origin0"
check "nothing renumbered: a's copy is still TASK-4" test -f "$work/a/backlog/tasks/task-4 - Mine.md"
check "no TASK-5 anywhere in a" sh -c '! ls "$1"/backlog/tasks | grep -q "^task-5 "' _ "$work/a"
check "the checks did not run" sh -c '! test -f "$1"' _ "$work/checks.log"
out=$(in_a bash "$SB" renumber 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
check "a manual renumber applies the same mapping" has "$out" "renumbered TASK-4 -> TASK-5"
integrate_a
check "integrate then exits 0 (rc=$rc)" test "$rc" -eq 0
check "origin has TASK-5 Mine" sh -c 'git --git-dir="$1" ls-tree -r --name-only master | grep -q "task-5 - Mine.md"' _ "$work/origin.git"

echo "# an interrupted merge is preserved, and a retry refuses until it is settled"
fresh
diverge
head0=$(clone_sha a)
printf '#!/bin/sh\nsleep 30\n' >"$work/a/.git/hooks/commit-msg"
chmod +x "$work/a/.git/hooks/commit-msg"
integrate_a SHARED_BACKLOG_DEADLINE=3
rm -f "$work/a/.git/hooks/commit-msg"
check "the deadline stops integrate (rc=$rc)" test "$rc" -ne 0
check "it reports the merge in progress" has "$out" "merge in progress"
check "MERGE_HEAD is kept" test -f "$work/a/.git/MERGE_HEAD"
check "HEAD did not move" test "$(clone_sha a)" = "$head0"
staged=$(in_a git diff --cached --name-only)
integrate_a
check "a retry exits 1 (rc=$rc)" test "$rc" -eq 1
check "it names the interrupted operation" has "$out" "interrupted operation"
check "the merge is still in progress" test -f "$work/a/.git/MERGE_HEAD"
check "the staged merge result is untouched" test "$(in_a git diff --cached --name-only)" = "$staged"
in_a git merge --abort
integrate_a
check "after an abort by hand integrate exits 0 (rc=$rc)" test "$rc" -eq 0

echo "# a non-fast-forward push is retried and then lands"
fresh
diverge
sneak_hook 1
integrate_a
check "integrate exits 0 (rc=$rc)" test "$rc" -eq 0
check "it pushed twice" test "$(pushes)" -eq 2
check "origin's tip is a's HEAD" test "$(origin_sha)" = "$(clone_sha a)"
trailer=$(git -C "$work/a" log -1 --format='%(trailers:key=Integrated-Origin,valueonly)' | tr -d '\n')
check "the second merge's trailer names the refetched origin SHA" test "$trailer" = "$(git -C "$work/a" rev-parse HEAD^2)"

echo "# a push refused every time gives up after 3 tries"
fresh
diverge
sneak_hook 99
integrate_a
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it pushed exactly 3 times" test "$(pushes)" -eq 3
check "it says the push was refused 3 times" has "$out" "push refused 3 times"
check "origin does not have a's work" sh -c '! git --git-dir="$1" log --format=%s master | grep -q "a work"' _ "$work/origin.git"

# fake_ssh MESSAGE — push through an ssh stub that prints MESSAGE, fails and
# counts its runs in $work/ssh.calls; fetch keeps the local URL.
fake_ssh() {
  : >"$work/ssh.calls"
  printf '#!/bin/sh\necho x >>"%s"\necho "%s" >&2\nexit 255\n' "$work/ssh.calls" "$1" >"$work/ssh"
  chmod +x "$work/ssh"
  in_a git config remote.origin.pushurl "ssh://git@example.invalid/origin.git"
}
ssh_calls() { wc -l <"$work/ssh.calls" | tr -d ' '; }

echo "# an auth failure is reported and not retried"
fresh
diverge
fake_ssh "git@example.invalid: Permission denied (publickey)."
integrate_a SHARED_BACKLOG_SSH="$work/ssh"
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it names an auth failure" has "$out" "push failed: auth"
check "it pushed once" test "$(ssh_calls)" -eq 1

echo "# an unreachable origin is reported and not retried"
fresh
diverge
fake_ssh "ssh: Could not resolve hostname example.invalid: Name or service not known"
integrate_a SHARED_BACKLOG_SSH="$work/ssh"
check "integrate exits 2 (rc=$rc)" test "$rc" -eq 2
check "it names an unreachable origin" has "$out" "origin unreachable"
check "it pushed once" test "$(ssh_calls)" -eq 1

echo "# a hook refusal is reported and not retried"
fresh
diverge
: >"$work/hook.calls"
printf '#!/bin/sh\necho x >>"%s"\nexit 1\n' "$work/hook.calls" >"$work/origin.git/hooks/pre-receive"
chmod +x "$work/origin.git/hooks/pre-receive"
origin0=$(origin_sha)
integrate_a
check "integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "it names a hook refusal" has "$out" "push failed: hook"
check "the server hook ran once" test "$(wc -l <"$work/hook.calls" | tr -d ' ')" -eq 1
check "origin unchanged" test "$(origin_sha)" = "$origin0"
rm -f "$work/origin.git/hooks/pre-receive"
printf '#!/bin/sh\necho x >>"%s"\nexit 1\n' "$work/hook.calls" >"$work/a/.git/hooks/pre-push"
chmod +x "$work/a/.git/hooks/pre-push"
: >"$work/hook.calls"
integrate_a
check "a refusing local pre-push hook: integrate exits 1 (rc=$rc)" test "$rc" -eq 1
check "the local hook ran once" test "$(wc -l <"$work/hook.calls" | tr -d ' ')" -eq 1
check "it names a hook refusal" has "$out" "push failed: hook"

echo
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
