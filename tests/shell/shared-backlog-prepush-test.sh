#!/usr/bin/env bash
# Scratch-repo tests for the plugin pre-push body plugins/ralph/git-hooks/pre-push
# (TASK-311). Every push goes through the real plugin shim
# (templates/shims/git-hook) installed by shared-backlog.sh enable, and a
# registry whose ralph entry is this repo's plugins/ralph, so the body and the
# shared-backlog.sh it runs are the shipped files, not stubs. It refuses a tip
# carrying a duplicate task or draft ID, and a push without the backlog CLI; it
# passes a ref deletion and a push of several refs; the switch, not the marker,
# decides; an existing pre-push keeps running as pre-push.local with the same
# stdin; and a real create push runs the hook while create holds the protocol
# lock, without deadlock. A last section pushes a bumped commit of a copy of
# this repo's plugin manifests through the shim with the version-bump guard as
# pre-push.local. Everything runs in a `mktemp -d`: a bare repo stands in for
# origin. Needs the backlog CLI and jq.
#
# Usage: bash tests/shell/shared-backlog-prepush-test.sh

set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
PLUGIN="$ROOT/plugins/ralph"
SB="$PLUGIN/scripts/shared-backlog.sh"
BODY="$PLUGIN/git-hooks/pre-push"
PROJECT_SHIM="$PLUGIN/skills/ralph-init/templates/shims/shared-backlog.sh"
GUARD="$ROOT/.claude/hooks/version-bump-guard.sh"
work=$(mktemp -d "${TMPDIR:-/tmp}/shared-backlog-prepush-test.XXXXXX")
work=$(cd "$work" && pwd -P)
trap 'rm -rf "$work"' EXIT

# Isolate git from the user's config (hooksPath, signing, identity, ralph.holder)
# and Claude from the user's plugin registry.
export HOME="$work/home"
export GIT_CONFIG_NOSYSTEM=1
export CLAUDE_CONFIG_DIR="$work/claude"
export SHARED_BACKLOG_ALLOW_UNRELEASED=1
unset RALPH_RUN_LOCK_TOKEN SHARED_BACKLOG_HOLDER SHARED_BACKLOG_DEADLINE SHARED_BACKLOG_SSH \
  GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE BASH_ENV
mkdir -p "$HOME" "$CLAUDE_CONFIG_DIR/plugins"
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

# registry INSTALL — register INSTALL as the user-scope ralph plugin.
registry() {
  printf '{"version": 2, "plugins": {"ralph@dddpaul-ralph": [{"scope": "user", "installPath": "%s", "version": "9.9.9"}]}}\n' \
    "$1" >"$CLAUDE_CONFIG_DIR/plugins/installed_plugins.json"
}
registry "$PLUGIN"

# fresh — rebuild origin.git and an enabled clone a. Origin holds TASK-1 to
# TASK-3 and an opted-in marker. Clone a had a pre-push of its own, which enable
# keeps as pre-push.local; it logs its stdin to local.log, and whether the
# protocol lock is held, to lock.log.
fresh() {
  rm -rf "$work/origin.git" "$work/seed" "$work/a" "$work"/*.log
  git init -q --bare "$work/origin.git"
  mkdir -p "$work/seed/backlog" "$work/seed/.claude"
  printf 'task_prefix: "task"\nstatuses: ["To Do", "In Progress", "Done"]\n' >"$work/seed/backlog/config.yml"
  for d in tasks drafts completed archive/tasks docs decisions; do
    mkdir -p "$work/seed/backlog/$d"; touch "$work/seed/backlog/$d/.gitkeep"
  done
  printf '{"pluginHooks": true, "sharedBacklog": true}\n' >"$work/seed/.claude/ralph.json"
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
  cat >"$work/a/.git/hooks/pre-push" <<EOF
#!/bin/sh
cat >>"$work/local.log"
if [ -d "\$(git rev-parse --git-common-dir)/shared-backlog-protocol.lock" ]; then
  echo held >>"$work/lock.log"
else
  echo free >>"$work/lock.log"
fi
EOF
  chmod +x "$work/a/.git/hooks/pre-push"
  in_a git config ralph.jq "$(command -v jq)"
  in_a bash "$SB" enable --holder @a >/dev/null || { echo "enable failed"; exit 1; }
}

in_a() { (cd "$work/a" && "$@"); }
origin_sha() { git --git-dir="$work/origin.git" rev-parse "${1:-master}"; }

# push ARGS... — git push from clone a; sets out and rc.
push() {
  out=$(in_a git push origin "$@" 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    /'
}

# commit_dup — commit a second task file carrying TASK-1's ID.
commit_dup() {
  in_a sh -c 'f=$(ls backlog/tasks/task-1\ -\ *.md) && sed "s/^title: .*/title: Copy/" "$f" >"backlog/tasks/task-1 - Copy.md" &&
    git add -A && git commit -q -m "duplicate TASK-1"'
}

echo "# bash -n"
check "bash -n the pre-push body" bash -n "$BODY"
check "bash -n this suite" bash -n "$0"

echo "# enable puts the shim in front and keeps the old hook as pre-push.local"
fresh
check "pre-push is the plugin shim" cmp -s "$work/a/.git/hooks/pre-push" "$PLUGIN/skills/ralph-init/templates/shims/git-hook"
check "the old hook is pre-push.local" grep -q local.log "$work/a/.git/hooks/pre-push.local"

echo "# a clean push passes, and pre-push.local gets the same stdin"
in_a sh -c 'echo two >>x.txt && git commit -q -am "clean change"'
sha=$(in_a git rev-parse HEAD)
push master
check "the push exits 0 (rc=$rc)" test "$rc" -eq 0
check "the body checked one ref" has "$out" "no duplicate task IDs in 1 pushed ref(s)"
check "origin has the commit" test "$(origin_sha)" = "$sha"
check "pre-push.local read the pushed ref line" grep -q "^refs/heads/master $sha refs/heads/master " "$work/local.log"

echo "# a tip carrying a duplicate task ID is refused"
before=$(origin_sha)
commit_dup
: >"$work/local.log"
push master
check "the push exits non-zero (rc=$rc)" test "$rc" -ne 0
check "it names the duplicate task ID" has "$out" "duplicate task IDs in"
check "it names the copy" has "$out" "task-1 - Copy.md"
check "it names the refused ref" has "$out" "refusing to push refs/heads/master -> refs/heads/master"
check "origin is unchanged" test "$(origin_sha)" = "$before"
check "pre-push.local ran first with the same stdin" grep -q "^refs/heads/master $(in_a git rev-parse HEAD) refs/heads/master " "$work/local.log"

echo "# a duplicate draft ID is refused"
fresh
in_a sh -c 'for t in A B; do printf -- "---\nid: draft-1\ntitle: %s\nstatus: To Do\n---\n" "$t" >"backlog/drafts/draft-1 - $t.md"; done &&
  git add -A && git commit -q -m "two drafts with one ID"'
before=$(origin_sha)
push master
check "the push exits non-zero (rc=$rc)" test "$rc" -ne 0
check "it names the duplicate draft ID" has "$out" "duplicate draft IDs in"
check "origin is unchanged" test "$(origin_sha)" = "$before"

echo "# without the backlog CLI the push is refused"
fresh
bl_dir=$(dirname "$(command -v backlog)")
nobl="$work/nobl"
mkdir -p "$nobl"
for t in git bash jq env; do
  p=$(command -v "$t") && [ "$(dirname "$p")" = "$bl_dir" ] && ln -sf "$p" "$nobl/$t"
done
nobl_path=$(printf '%s\n' "$PATH" | tr ':' '\n' | grep -vxF "$bl_dir" | tr '\n' ':')
nobl_path="$nobl:${nobl_path%:}"
check "backlog is not on the trimmed PATH" sh -c '! PATH="$1" command -v backlog >/dev/null' _ "$nobl_path"
in_a sh -c 'echo three >>x.txt && git commit -q -am "change without backlog"'
before=$(origin_sha)
out=$(cd "$work/a" && PATH="$nobl_path" git push origin master 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/    /'
check "the push exits non-zero (rc=$rc)" test "$rc" -ne 0
check "it says backlog is not on PATH" has "$out" "backlog not on PATH"
check "origin is unchanged" test "$(origin_sha)" = "$before"

echo "# a ref deletion passes, and so does a push of several refs"
fresh
in_a sh -c 'git checkout -q -b side && echo side >side.txt && git add side.txt && git commit -q -m side && git checkout -q master &&
  echo four >>x.txt && git commit -q -am "master change"'
push master side
check "a push of two refs exits 0 (rc=$rc)" test "$rc" -eq 0
check "the body checked both refs" has "$out" "no duplicate task IDs in 2 pushed ref(s)"
check "origin has side" test "$(origin_sha side)" = "$(in_a git rev-parse side)"
in_a sh -c 'git checkout -q side && f=$(ls backlog/tasks/task-2\ -\ *.md) && cp "$f" "backlog/tasks/task-2 - Again.md" &&
  git add -A && git commit -q -m "duplicate TASK-2" && git checkout -q master && echo five >>x.txt && git commit -q -am "fine"'
before_side=$(origin_sha side)
push master side
check "two refs, one with a duplicate: the push exits non-zero (rc=$rc)" test "$rc" -ne 0
check "it refuses the side ref" has "$out" "refusing to push refs/heads/side -> refs/heads/side"
check "side on origin is unchanged" test "$(origin_sha side)" = "$before_side"
push :side
check "a deletion exits 0 (rc=$rc)" test "$rc" -eq 0
check "the body checked no ref for it" has "$out" "no duplicate task IDs in 0 pushed ref(s)"
check "side is gone from origin" sh -c '! git --git-dir="$1" rev-parse -q --verify refs/heads/side >/dev/null' _ "$work/origin.git"

echo "# the switch decides, not the marker"
fresh
in_a sh -c 'git rm -q .claude/ralph.json && git commit -q -m "drop the marker"'
commit_dup
before=$(origin_sha)
push master
check "with the marker gone and the switch on, a duplicate is refused (rc=$rc)" test "$rc" -ne 0
check "origin is unchanged" test "$(origin_sha)" = "$before"
in_a bash "$SB" disable >/dev/null
push master
check "with the switch off the same push passes (rc=$rc)" test "$rc" -eq 0

echo "# a real create through the installed shims runs the hook under create's lock"
fresh
mkdir -p "$work/a/scripts"
cp "$PROJECT_SHIM" "$work/a/scripts/shared-backlog.sh"
printf 'case "$0" in */git-hooks/pre-push|*/scripts/shared-backlog.sh) echo "$0 $*" >>"%s" ;; esac\n' \
  "$work/trace.log" >"$work/trace.sh"
start=$(date +%s)
out=$(cd "$work/a" && BASH_ENV="$work/trace.sh" SHARED_BACKLOG_DEADLINE=60 bash scripts/shared-backlog.sh create "Through the hook" 2>&1); rc=$?
elapsed=$(($(date +%s) - start))
printf '%s\n' "$out" | sed 's/^/    /'
sed 's/^/    trace: /' "$work/trace.log"
check "create exits 0 (rc=$rc) in ${elapsed}s, before its deadline" test "$rc" -eq 0 -a "$elapsed" -lt 60
check "it created TASK-4" has "$out" "created TASK-4 "
check "origin has TASK-4" sh -c 'git --git-dir="$1" ls-tree -r --name-only master backlog/tasks | grep -q "^backlog/tasks/task-4 - "' _ "$work/origin.git"
check "pre-push.local ran while the protocol lock was held" test "$(cat "$work/lock.log" 2>/dev/null)" = held
check "the plugin pre-push body ran" grep -q "^$BODY origin " "$work/trace.log"
check "the body ran check-dupes on the pushed commit" \
  grep -qx "$SB check-dupes $(origin_sha)" "$work/trace.log"
check "the protocol lock is released" test ! -e "$work/a/.git/shared-backlog-protocol.lock"

echo "# this repo's version-bump guard keeps running as pre-push.local"
if [ ! -x "$GUARD" ]; then
  nok "$GUARD is missing"
else
  rm -rf "$work/origin.git" "$work/v"
  git init -q --bare "$work/origin.git"
  mkdir -p "$work/v/.claude/hooks/lib" "$work/v/.claude-plugin" "$work/v/plugins/ralph/.claude-plugin" "$work/v/plugins/ralph/skills/x"
  cp "$GUARD" "$work/v/.claude/hooks/"
  cp "$ROOT/.claude/hooks/lib/"*.sh "$work/v/.claude/hooks/lib/"
  manifests() {
    printf '{"name": "ralph", "version": "%s"}\n' "$1" >"$work/v/plugins/ralph/.claude-plugin/plugin.json"
    printf '{"name": "dddpaul-ralph", "plugins": [{"name": "ralph", "source": "./plugins/ralph", "version": "%s"}]}\n' \
      "$1" >"$work/v/.claude-plugin/marketplace.json"
  }
  manifests 1.0.0
  echo a >"$work/v/plugins/ralph/skills/x/SKILL.md"
  (
    cd "$work/v" && git init -q && git add -A && git commit -q -m init &&
      git remote add origin "$work/origin.git" && git push -q origin master &&
      git tag -a v1.0.0 -m v1.0.0 && git push -q origin v1.0.0
  ) || nok "version-bump scratch repo setup failed"
  # This repo's pre-push wrapper, kept as pre-push.local behind the plugin shim.
  cp "$ROOT/plugins/ralph/skills/ralph-init/templates/shims/git-hook" "$work/v/.git/hooks/pre-push"
  printf '#!/bin/bash\nexec "$(git rev-parse --show-toplevel)/.claude/hooks/version-bump-guard.sh" "$@"\n' \
    >"$work/v/.git/hooks/pre-push.local"
  chmod +x "$work/v/.git/hooks/pre-push" "$work/v/.git/hooks/pre-push.local"
  git -C "$work/v" config ralph.pluginHooks true
  git -C "$work/v" config ralph.jq "$(command -v jq)"
  echo b >"$work/v/plugins/ralph/skills/x/SKILL.md"
  git -C "$work/v" commit -q -am "shipped change without a bump"
  out=$(cd "$work/v" && git push origin master 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    /'
  check "an unbumped shipped change is refused by the guard (rc=$rc)" test "$rc" -ne 0
  check "the refusal comes from the version-bump guard" has "$out" "plugin version was not bumped"
  manifests 1.0.1
  (cd "$work/v" && git commit -q -am "bump to 1.0.1" && git tag -a v1.0.1 -m v1.0.1) || nok "bump commit failed"
  out=$(cd "$work/v" && git push --follow-tags origin master 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    /'
  check "the bumped push passes the guard and the plugin body (rc=$rc)" test "$rc" -eq 0
  check "origin has the bumped commit" test "$(origin_sha)" = "$(git -C "$work/v" rev-parse HEAD)"
fi

echo
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
