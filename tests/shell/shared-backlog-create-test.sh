#!/usr/bin/env bash
# Scratch-repo tests for how create of plugins/ralph/scripts/shared-backlog.sh
# allocates a task ID in a detached temporary worktree (TASK-307): it publishes
# an ID free on origin from clones that are behind origin, ahead of it, dirty or
# on a task branch, and leaves their branch, index and working tree alone; it
# refuses offline before allocating; its Shared-Backlog-Op trailer survives a
# retry; the clone's hooks resolve the plugin with the clone's identity in the
# worktree; sync and integrate refuse while an untracked task file is around.
# Everything runs in a `mktemp -d`: one bare repo stands in for origin and two
# clones (a, b) for two hosts. Never touches a real origin. Needs the backlog
# CLI; the plugin-lookup section also needs jq.
#
# Usage: bash tests/shell/shared-backlog-create-test.sh

set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SB="$ROOT/plugins/ralph/scripts/shared-backlog.sh"
SHIM="$ROOT/plugins/ralph/skills/ralph-init/templates/shims/git-hook"
work=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-create-test.XXXXXX")
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

# fresh — rebuild origin.git and the clones a and b. Origin holds TASK-1 to
# TASK-3 and x.txt.
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

# origin_ids — task IDs on origin's master, space-separated.
origin_ids() {
  git --git-dir="$work/origin.git" ls-tree -r --name-only master backlog/tasks |
    sed -n 's|^backlog/tasks/task-\([0-9]*\) - .*|\1|p' | sort -n | tr '\n' ' '
}
origin_dupes() {
  git --git-dir="$work/origin.git" ls-tree -r --name-only master backlog/tasks |
    sed -n 's|^backlog/tasks/task-\([0-9]*\) - .*|\1|p' | sort | uniq -d
}
op_of() { git --git-dir="$work/origin.git" log -1 --format='%(trailers:key=Shared-Backlog-Op,valueonly)' "$1" | grep .; }

# snapshot DIR — branch, HEAD, index and working tree of the clone in DIR.
snapshot() {
  (
    cd "$1" || exit 1
    git symbolic-ref -q HEAD || echo detached
    git rev-parse HEAD
    git status --porcelain=v1 --untracked-files=all
    git diff --cached
    git diff
    find . -path ./.git -prune -o -type f -print | sort | while IFS= read -r f; do
      printf '%s ' "$f"; cksum <"$f"
    done
  )
}
worktrees() { git -C "$work/$1" worktree list --porcelain | grep -c '^worktree '; }
leftover_tmp() { ls -d "${TMPDIR:-/tmp}"/shared-backlog-create.* 2>/dev/null | grep -c . ; }

# create_in CLONE LABEL TITLE — run create in CLONE and check that it publishes
# a fresh ID on origin and leaves the clone as it was.
create_in() {
  local c=$1 label=$2 title=$3 before after ids_before out rc id
  before=$(snapshot "$work/$c")
  ids_before=$(origin_ids)
  out=$( (cd "$work/$c" && bash "$SB" create "$title") 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    /'
  after=$(snapshot "$work/$c")
  id=$(printf '%s\n' "$out" | sed -n 's/^created TASK-\([0-9]*\) .*/\1/p')
  check "$label: create exits 0 (rc=$rc)" test "$rc" -eq 0
  check "$label: the new ID $id was free on origin before" sh -c 'test -n "$1" && ! printf " %s" "$2" | grep -q " $1 "' _ "$id" "$ids_before"
  check "$label: origin now has TASK-$id" sh -c 'printf " %s" "$1" | grep -q " $2 "' _ "$(origin_ids)" "$id"
  check "$label: origin has no duplicate IDs" test -z "$(origin_dupes)"
  check "$label: origin's tip is 'task-$id: add task'" \
    test "$(git --git-dir="$work/origin.git" log -1 --format=%s master)" = "task-$id: add task"
  check "$label: branch, index and working tree unchanged" test "$before" = "$after"
  check "$label: no temporary worktree left" test "$(worktrees "$c")" -eq 1
}

echo "# bash -n"
check "bash -n shared-backlog.sh" bash -n "$SB"
check "bash -n this suite" bash -n "$0"

echo "# create from clones in every state"
tmp_before=$(leftover_tmp)
fresh
in_b bash "$SB" create "From b" >/dev/null 2>&1
create_in a "behind origin" "Behind"
in_a git pull -q --ff-only origin master
in_a sh -c 'echo ahead >>x.txt && git commit -q -am "local unpushed"'
create_in a "ahead of origin" "Ahead"
fresh
in_a sh -c 'echo dirty >>x.txt && echo staged >>y.txt && git add y.txt && echo new >scratch.txt'
create_in a "dirty" "Dirty"
fresh
in_a sh -c 'git checkout -q -b task-9 && echo branch >>x.txt && git commit -q -am "task-9: work" && echo wip >>y.txt'
create_in a "on a task branch" "Branch"
check "no temporary directory left behind" test "$(leftover_tmp)" -eq "$tmp_before"

echo "# the operation ID is fixed once and reused on a retry"
fresh
: >"$work/sneaks"
: >"$work/ops"
cat >"$work/a/.git/hooks/pre-push" <<EOF
#!/bin/sh
git log -1 --format='%(trailers:key=Shared-Backlog-Op,valueonly)' HEAD | grep . >>"$work/ops"
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
[ -s "$work/sneaks" ] && exit 0
echo x >>"$work/sneaks"
cd "$work/b" && git pull -q --ff-only origin master &&
  echo sneak >>x.txt && git commit -q -am "unrelated" && git push -q origin master
EOF
chmod +x "$work/a/.git/hooks/pre-push"
out=$(in_a bash "$SB" create "Retried" 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
check "the create exits 0 (rc=$rc)" test "$rc" -eq 0
check "it pushed twice" test "$(wc -l <"$work/ops" | tr -d ' ')" -eq 2
check "both pushes carried one operation ID" test "$(sort -u "$work/ops" | wc -l | tr -d ' ')" -eq 1
check "origin's tip carries that ID" test "$(op_of master)" = "$(head -1 "$work/ops")"
check "origin's tip is 'task-4: add task' on top of the unrelated commit" \
  test "$(git --git-dir="$work/origin.git" log -2 --format=%s master | tr '\n' '|')" = "task-4: add task|unrelated|"
rm -f "$work/a/.git/hooks/pre-push"
in_a bash "$SB" sync >/dev/null 2>&1
out2=$(in_a bash "$SB" create "Another" 2>&1)
check "a second create gets a new operation ID" test "$(op_of master)" != "$(head -1 "$work/ops")"
printf '%s\n' "$out2" | sed 's/^/    /'

echo "# offline, create refuses before it allocates"
fresh
in_a git remote set-url origin "$work/nowhere.git"
before=$(snapshot "$work/a")
refs_before=$(in_a git for-each-ref)
out=$(in_a bash "$SB" create "Offline" 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
check "create exits 2 (rc=$rc)" test "$rc" -eq 2
check "it says origin is unreachable" has "$out" "origin unreachable"
check "no commit and no ref changed" test "$(in_a git for-each-ref)" = "$refs_before"
check "no task file and nothing else changed" test "$(snapshot "$work/a")" = "$before"
check "no Offline task file anywhere in the clone" sh -c '! find "$1" -name "task-*Offline*" | grep -q .' _ "$work/a"
check "no temporary worktree left" test "$(worktrees a)" -eq 1
check "origin unchanged" test "$(origin_ids)" = "1 2 3 "

echo "# sync and integrate refuse while an untracked task file is around"
fresh
printf '%s\n' --- 'id: task-9' 'title: Stray' --- >"$work/a/backlog/tasks/task-9 - Stray.md"
head0=$(in_a git rev-parse HEAD)
in_b bash "$SB" create "Elsewhere" >/dev/null 2>&1
for c in sync integrate; do
  out=$(in_a bash "$SB" "$c" 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    /'
  check "$c exits 1 (rc=$rc)" test "$rc" -eq 1
  check "$c lists the untracked task file" has "$out" "backlog/tasks/task-9 - Stray.md"
done
check "the refusals left master where it was" test "$(in_a git rev-parse HEAD)" = "$head0"
in_a rm "backlog/tasks/task-9 - Stray.md"
check "sync passes once the file is gone" sh -c '(cd "$1" && bash "$2" sync) 2>/dev/null' _ "$work/a" "$SB"

echo "# hooks in the temporary worktree resolve the plugin with the clone's identity"
if ! command -v jq >/dev/null 2>&1; then
  nok "jq is not installed; cannot drive the plugin-lookup shim"
else
  fresh
  plugin="$work/fake-plugin"
  mkdir -p "$plugin/git-hooks"
  for h in commit-msg post-commit; do
    printf '#!/bin/sh\necho "%s $(pwd -P) $(git log -1 --format=%%s 2>/dev/null)" >>"%s"\n' \
      "$h" "$work/hook.log" >"$plugin/git-hooks/$h"
    chmod +x "$plugin/git-hooks/$h"
    cp "$SHIM" "$work/a/.git/hooks/$h"
    chmod +x "$work/a/.git/hooks/$h"
  done
  in_a git config ralph.pluginHooks true
  export CLAUDE_CONFIG_DIR="$work/claude"
  mkdir -p "$CLAUDE_CONFIG_DIR/plugins"
  # registry ID — only a project-scope entry for ID, so the lookup succeeds
  # only when the hook resolves with that project identity.
  registry() {
    printf '{"version": 2, "plugins": {"ralph@dddpaul-ralph": [{"scope": "project", "projectPath": "%s", "installPath": "%s", "version": "9.9.9"}]}}\n' \
      "$1" "$plugin" >"$CLAUDE_CONFIG_DIR/plugins/installed_plugins.json"
  }
  clone_id=$(cd "$work/a" && pwd -P)
  registry "$work/elsewhere"
  : >"$work/hook.log"
  out=$(in_a bash "$SB" create "Wrong identity" 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    /'
  check "with another project's entry the commit is blocked (rc=$rc)" test "$rc" -eq 1
  check "and nothing reached origin" test "$(origin_ids)" = "1 2 3 "
  registry "$clone_id"
  : >"$work/hook.log"
  out=$(in_a bash "$SB" create "Right identity" 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    /'
  sed 's/^/    log: /' "$work/hook.log"
  check "with the clone's entry create exits 0 (rc=$rc)" test "$rc" -eq 0
  check "the plugin commit-msg body ran in the temporary worktree" \
    grep -q "^commit-msg .*/shared-backlog-create\.[^/]*/wt " "$work/hook.log"
  check "the plugin post-commit body saw the real commit" \
    grep -q "^post-commit .*/shared-backlog-create\.[^/]*/wt task-4: add task$" "$work/hook.log"
  check "origin has TASK-4" test "$(origin_ids)" = "1 2 3 4 "
  unset CLAUDE_CONFIG_DIR
fi

echo
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
