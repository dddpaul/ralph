#!/usr/bin/env bash
# Scratch-repo tests for the claim rules, the holder, check-dupes and --help of
# plugins/ralph/scripts/shared-backlog.sh (TASK-305). Everything runs in a
# `mktemp -d`: one bare repo stands in for origin and one clone for a host.
# Never touches a real origin. Needs the backlog CLI.
#
# Usage: bash tests/shell/shared-backlog-claim-test.sh

set -u

SB="$(cd "$(dirname "$0")/../.." && pwd)/plugins/ralph/scripts/shared-backlog.sh"
work=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-claim-test.XXXXXX")
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

# fresh — rebuild origin.git and the clone a. Origin holds:
#   1 To Do, no assignee            2 @claude
#   3 @host-b                       4 @host-a and @host-b
#   5 @host-a                       6 @host-a, In Progress
#   7 @host-a, depends on 1         8 @claude and @host-b
#   9 @claude and @host-a           10-12 To Do, no assignee
fresh() {
  rm -rf "$work/origin.git" "$work/seed" "$work/a"
  git init -q --bare "$work/origin.git"
  mkdir -p "$work/seed/backlog"
  printf 'task_prefix: "task"\nstatuses: ["To Do", "In Progress", "Done"]\n' >"$work/seed/backlog/config.yml"
  for d in tasks drafts completed archive/tasks docs decisions; do
    mkdir -p "$work/seed/backlog/$d"; touch "$work/seed/backlog/$d/.gitkeep"
  done
  (
    cd "$work/seed" && git init -q &&
      backlog task create "Plain" >/dev/null &&
      backlog task create "Generic" -a @claude >/dev/null &&
      backlog task create "Taken" -a @host-b >/dev/null &&
      backlog task create "Shared" -a @host-a -a @host-b >/dev/null &&
      backlog task create "Mine" -a @host-a >/dev/null &&
      backlog task create "Mine in progress" -a @host-a -s "In Progress" >/dev/null &&
      backlog task create "Mine with open dep" -a @host-a --dep task-1 >/dev/null &&
      backlog task create "Generic and other" -a @claude -a @host-b >/dev/null &&
      backlog task create "Generic and mine" -a @claude -a @host-a >/dev/null &&
      backlog task create "Ten" >/dev/null &&
      backlog task create "Eleven" >/dev/null &&
      backlog task create "Twelve" >/dev/null &&
      git add -A && git commit -q -m init &&
      git remote add origin "$work/origin.git" && git push -q origin master
  ) || { echo "seed failed"; exit 1; }
  git clone -q "$work/origin.git" "$work/a"
}

sb() { (cd "$work/a" && bash "$SB" "$@"); }
origin_sha() { git --git-dir="$work/origin.git" rev-parse master; }

# who N — TASK-N's assignees on origin, space-separated.
who() {
  local p
  p=$(git --git-dir="$work/origin.git" ls-tree -r --name-only master backlog/tasks |
    grep "^backlog/tasks/task-$1 - ")
  git --git-dir="$work/origin.git" show "master:$p" |
    awk 'NR > 1 && /^---$/ { exit } inl && /^ +- / { v = $0; sub(/^ +- +/, "", v); gsub(/\047/, "", v); o = o v " "; next }
         inl { exit } /^assignee:/ { inl = 1 } END { sub(/ $/, "", o); print o }'
}

# --- assignees --------------------------------------------------------------

fresh
check "a bare @claude assignee is unassigned: claim succeeds" sb claim 2 --as @host-a
check "the claim replaces @claude with the holder" test "$(who 2)" = "@host-a"

before=$(origin_sha)
out=$(sb claim 3 --as @host-a 2>&1); rc=$?
check "another holder alone means taken (rc=$rc)" test "$rc" -eq 1
check "the refusal names the other holder" has "$out" "taken by @host-b"

out=$(sb claim 4 --as @host-a 2>&1); rc=$?
check "another holder among several, the holder included, means taken (rc=$rc)" test "$rc" -eq 1
check "the refusal names only the other holder" has "$out" "taken by @host-b"

out=$(sb claim 8 --as @host-a 2>&1); rc=$?
check "@claude beside another holder still means taken (rc=$rc)" test "$rc" -eq 1
check "the refusal leaves @claude out" sh -c 'case "$1" in *"taken by @host-b"*) ! printf "%s" "$1" | grep -q "taken by.*@claude" ;; *) exit 1 ;; esac' _ "$out"
check "refused claims push nothing" test "$(origin_sha)" = "$before"
check "the refusal points at --force" has "$out" "--force takes it over"

# --- --force takes over -----------------------------------------------------

fresh
out=$(sb claim 3 --as @host-a --force 2>&1); rc=$?
check "--force takes over another holder's task (rc=$rc)" test "$rc" -eq 0
check "the takeover names the old holder" has "$out" "taken by @host-b; --force takes it over"
check "the takeover leaves only the holder" test "$(who 3)" = "@host-a"
check "--force takes over a task the holder shares with another" sb claim 4 --as @host-a --force
check "the shared task keeps only the holder" test "$(who 4)" = "@host-a"
fresh
before=$(origin_sha)

# --- already held -----------------------------------------------------------

out=$(sb claim 5 --as @host-a 2>&1); rc=$?
check "a held To Do claim with done deps is accepted (rc=$rc)" test "$rc" -eq 0
check "it reports the existing claim" has "$out" "already claimed by @host-a"
check "an accepted held claim pushes nothing" test "$(origin_sha)" = "$before"

out=$(sb claim 6 --as @host-a 2>&1); rc=$?
check "a held claim that is not To Do is refused (rc=$rc)" test "$rc" -eq 1
check "the refusal names the status" has "$out" "'In Progress', not To Do"

out=$(sb claim 7 --as @host-a 2>&1); rc=$?
check "a held claim with an unfinished dependency is refused (rc=$rc)" test "$rc" -eq 1
check "the refusal names the dependency" has "$out" "unfinished dependencies"

check "a held claim beside @claude is accepted" sb claim 9 --as @host-a
check "the already-held checks push nothing" test "$(origin_sha)" = "$before"

# --- the holder -------------------------------------------------------------

(cd "$work/a" && git config ralph.holder @cfg)
check "--as beats the environment and git config" sh -c '(cd "$1" && SHARED_BACKLOG_HOLDER=@env bash "$2" claim 10 --as @arg) 2>/dev/null' _ "$work/a" "$SB"
check "the claim goes to the --as holder" test "$(who 10)" = "@arg"
check "SHARED_BACKLOG_HOLDER beats git config" sh -c '(cd "$1" && SHARED_BACKLOG_HOLDER=@env bash "$2" claim 11) 2>/dev/null' _ "$work/a" "$SB"
check "the claim goes to the environment holder" test "$(who 11)" = "@env"
check "git config ralph.holder is the last resort" sh -c '(cd "$1" && bash "$2" claim 12) 2>/dev/null' _ "$work/a" "$SB"
check "the claim goes to the configured holder" test "$(who 12)" = "@cfg"

(cd "$work/a" && git config --unset ralph.holder)
before=$(origin_sha)
out=$(sb claim 1 2>&1); rc=$?
check "a missing holder is an error (rc=$rc)" test "$rc" -eq 1
check "the error names all three sources" has "$out" "pass --as @name, set SHARED_BACKLOG_HOLDER or git config ralph.holder"
out=$(sb release 2 2>&1); rc=$?
check "release with no holder is an error too (rc=$rc)" test "$rc" -eq 1
out=$(sb claim 1 --as @claude 2>&1); rc=$?
check "the generic @claude is refused as a holder (rc=$rc)" test "$rc" -eq 1
check "the holder errors push nothing" test "$(origin_sha)" = "$before"

# --- check-dupes ------------------------------------------------------------

fresh
check "check-dupes passes on a clean HEAD" sb check-dupes

# A side commit whose config says "proj" and carries two proj-5 files and two
# draft-1 files, while the working tree's config still says "task".
(
  cd "$work/a" && git checkout -q -b side &&
    printf 'task_prefix: "proj"\n' >backlog/config.yml &&
    printf -- '---\nid: PROJ-5\ntitle: A\nstatus: To Do\n---\n' >"backlog/tasks/proj-5 - A.md" &&
    printf -- '---\nid: PROJ-5\ntitle: B\nstatus: To Do\n---\n' >"backlog/tasks/proj-5 - B.md" &&
    git add -A && git commit -q -m "proj dupes" &&
    git checkout -q master &&
    git checkout -q -b drafts &&
    printf -- '---\nid: DRAFT-1\ntitle: A\nstatus: To Do\n---\n' >"backlog/drafts/draft-1 - A.md" &&
    printf -- '---\nid: DRAFT-1\ntitle: B\nstatus: To Do\n---\n' >"backlog/drafts/draft-1 - B.md" &&
    git add -A && git commit -q -m "draft dupes" &&
    git checkout -q master
) || { echo "check-dupes setup failed"; exit 1; }

out=$(sb check-dupes side 2>&1); rc=$?
check "check-dupes REV reads the task prefix from REV (rc=$rc)" test "$rc" -eq 1
check "its own duplicate report finds REV's prefix" has "$out" "duplicate task IDs in side:"
check "it names the duplicate under REV's prefix" has "$out" "  backlog/tasks/proj-5 - B.md"
check "the working tree's config stays as it was" grep -q '"task"' "$work/a/backlog/config.yml"

out=$(sb check-dupes drafts 2>&1); rc=$?
check "check-dupes includes drafts (rc=$rc)" test "$rc" -eq 1
check "it names the duplicate drafts" has "$out" "duplicate draft IDs"
check "it lists both draft files" has "$out" "backlog/drafts/draft-1 - B.md"

empty=$(cd "$work/a" && git commit-tree "$(git hash-object -t tree /dev/null)" -m empty)
out=$(sb check-dupes "$empty" 2>&1); rc=$?
check "check-dupes passes on a REV without backlog/ (rc=$rc)" test "$rc" -eq 0
check "and says so explicitly" has "$out" "has no backlog/ directory"

# A PATH with every directory that holds backlog replaced by a copy of its
# other entries, so git and the coreutils stay reachable.
nobl="$work/nobl-bin"
mkdir -p "$nobl"
path=''
IFS=: read -r -a dirs <<EOF
$PATH
EOF
for d in "${dirs[@]}"; do
  if [ -x "$d/backlog" ]; then
    for e in "$d"/*; do
      [ "${e##*/}" = backlog ] || ln -sf "$e" "$nobl/" 2>/dev/null
    done
  else
    path="$path${path:+:}$d"
  fi
done
out=$( (cd "$work/a" && PATH="$nobl:$path" bash "$SB" check-dupes) 2>&1); rc=$?
check "check-dupes fails when backlog is missing (rc=$rc)" test "$rc" -eq 1
check "it names the missing executable" has "$out" "backlog not on PATH"

# --- help -------------------------------------------------------------------

out=$(cd "$work" && bash "$SB" --help 2>/dev/null); rc=$?
check "--help exits 0 outside a repo (rc=$rc)" test "$rc" -eq 0
check "--help prints the usage" has "$out" "Usage: scripts/shared-backlog.sh"
check "--help prints the exit codes in full" has "$out" "64 usage error"
check "--help prints the last header line" has "$out" "64 usage error. Bash 3.2 clean"
out=$(sb -h 2>/dev/null); rc=$?
check "-h exits 0 and prints the help (rc=$rc)" sh -c 'test "$1" -eq 0 && case "$2" in *"64 usage error"*) ;; *) exit 1 ;; esac' _ "$rc" "$out"
out=$(sb no-such-command 2>&1 >/dev/null); rc=$?
check "an unknown command is still a usage error (rc=$rc)" test "$rc" -eq 64
check "the usage error prints the whole help on stderr" has "$out" "64 usage error"
mkdir -p "$work/bin" && cp "$SB" "$work/bin/sb.sh"
out=$( (cd "$work/a/backlog" && bash ../../bin/sb.sh no-such-command) 2>&1); rc=$?
check "a usage error from a subdirectory still prints the help (rc=$rc)" sh -c 'test "$1" -eq 64 && case "$2" in *"64 usage error"*) ;; *) exit 1 ;; esac' _ "$rc" "$out"

echo
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
