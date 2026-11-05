#!/usr/bin/env bats
# Unit tests for .claude/hooks/version-bump-guard.sh — the pre-push guard that
# blocks a master push which changes shipped plugin files without a strictly
# greater plugin version (so `/plugin update` rebuilds the consumer cache),
# and refuses a push whose version tag on origin does not peel to the tip's
# release commit. See TASK-214 and TASK-319.

load '../helpers/common'
HOOK="$PROJECT_ROOT/.claude/hooks/version-bump-guard.sh"
MANIFEST="plugins/ralph/.claude-plugin/plugin.json"
MARKET=".claude-plugin/marketplace.json"
SHIPPED="plugins/ralph/skills/ralph-run/SKILL.md"
ZERO="0000000000000000000000000000000000000000"

# Write both manifests with the given version (the marketplace one with $2
# when given, to make them disagree).
set_version() {
  mkdir -p "$(dirname "$MANIFEST")" "$(dirname "$MARKET")"
  printf '{\n  "name": "ralph",\n  "version": "%s"\n}\n' "$1" > "$MANIFEST"
  printf '{\n  "metadata": {\n    "version": "%s"\n  }\n}\n' "${2:-$1}" > "$MARKET"
}

# Publish a commit on origin as master (so origin has its objects).
publish() { # $1=sha
  git push -q -f origin "$1:refs/heads/master"
}

# Tag a commit on origin only: lightweight, or annotated with $3=annotated.
origin_tag() { # $1=tag $2=sha [$3=annotated]
  git push -q -f origin "$2:refs/heads/tagged-$1"
  if [ "${3:-}" = "annotated" ]; then
    git -C "$ORIGIN" -c user.name=Test -c user.email=test@example.com tag -a "$1" -m "ralph $1" "$2"
  else
    git -C "$ORIGIN" tag "$1" "$2"
  fi
}

# Feed one master ref-update line to the guard: <local> <remote>.
run_guard() { # $1=local_sha $2=remote_sha [$3=remote_ref]
  local ref="${3:-refs/heads/master}"
  run bash "$HOOK" <<EOF
refs/heads/master $1 $ref $2
EOF
}

setup() {
  TEST_DIR="$(make_temp_dir)"
  ORIGIN="$TEST_DIR/origin.git"
  git init -q --bare "$ORIGIN"
  mkdir "$TEST_DIR/work"
  cd "$TEST_DIR/work"
  git init -q -b master
  git remote add origin "$ORIGIN"
  git config user.email test@example.com
  git config user.name Test

  # Base commit: manifest at 0.1.0, a shipped skill file, and a docs file.
  set_version "0.1.0"
  mkdir -p "$(dirname "$SHIPPED")"
  echo "base skill" > "$SHIPPED"
  echo "# readme" > README.md
  git add -A
  git commit -q -m "base"
  BASE=$(git rev-parse HEAD)
  publish "$BASE"
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

@test "blocks: shipped file changed without a version bump" {
  echo "changed skill" > "$SHIPPED"
  git commit -q -am "edit skill, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "passes: shipped file changed with a version bump" {
  echo "changed skill" > "$SHIPPED"
  set_version "0.2.0"
  git commit -q -am "edit skill + bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 0 ]
}

@test "passes: docs-only change (no shipped file touched)" {
  echo "# readme v2" > README.md
  git commit -q -am "docs only, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 0 ]
}

@test "passes: non-master push even when shipped changed without bump" {
  echo "changed skill" > "$SHIPPED"
  git commit -q -am "edit skill, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE" "refs/heads/feature"
  [ "$status" -eq 0 ]
}

@test "passes: first push (remote sha all-zeros) even when shipped changed" {
  echo "changed skill" > "$SHIPPED"
  git commit -q -am "edit skill, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$ZERO"
  [ "$status" -eq 0 ]
}

@test "blocks: version regression (lower) with shipped change" {
  set_version "0.2.0"
  echo "v020 skill" > "$SHIPPED"
  git commit -q -am "at 0.2.0"
  local hi; hi=$(git rev-parse HEAD)
  # Now "push" the base (0.1.0) over a remote that is at 0.2.0: not greater.
  echo "changed again" > "$SHIPPED"
  set_version "0.1.5"
  git commit -q -am "regress-ish 0.1.5"
  local lo; lo=$(git rev-parse HEAD)

  run_guard "$lo" "$hi"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "passes: only .claude/backlog tooling changed (excluded from shipped set)" {
  mkdir -p backlog/tasks .claude/hooks
  echo "task" > backlog/tasks/task-1.md
  echo "hook" > .claude/hooks/example.sh
  git add -A
  git commit -q -m "tooling only, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 0 ]
}

@test "blocks: plugin hook changed without a version bump" {
  mkdir -p plugins/ralph/hooks
  echo '{"hooks": {}}' > plugins/ralph/hooks/hooks.json
  git add -A
  git commit -q -m "plugin hook, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "blocks: user-settings fragment changed without a version bump" {
  echo '{"permissions": {"allow": []}}' > plugins/ralph/user-settings.json
  git add -A
  git commit -q -m "fragment, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "blocks: plugin git-hooks body changed without a version bump" {
  mkdir -p plugins/ralph/git-hooks
  echo "hook body" > plugins/ralph/git-hooks/pre-push
  git add -A
  git commit -q -m "git hook body, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "blocks: plugin script changed without a version bump" {
  mkdir -p plugins/ralph/scripts
  echo "script" > plugins/ralph/scripts/shared-backlog.sh
  git add -A
  git commit -q -m "script, no bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

# --- release tag check (TASK-319) -------------------------------------------

# Commit a 0.2.0 bump on top of $1 that also writes $2 to the docs file $3.
bump_020_from() { # $1=parent $2=content $3=file
  git checkout -q "$1"
  set_version "0.2.0"
  mkdir -p "$(dirname "$3")"
  echo "$2" > "$3"
  git add -A
  git commit -q -m "bump 0.2.0: $2"
  git rev-parse HEAD
}

@test "passes: normal bump with no tag on origin yet" {
  local b1; b1=$(bump_020_from "$BASE" "host B" design/b.md)

  run_guard "$b1" "$BASE"
  [ "$status" -eq 0 ]
}

@test "passes: normal bump whose tag on origin points at the release commit" {
  local b1; b1=$(bump_020_from "$BASE" "host B" design/b.md)
  origin_tag v0.2.0 "$b1"

  run_guard "$b1" "$BASE"
  [ "$status" -eq 0 ]
}

@test "blocks: both sides tag the same version with different content" {
  local a1 b1
  a1=$(bump_020_from "$BASE" "host A" design/a.md)
  origin_tag v0.2.0 "$a1"
  b1=$(bump_020_from "$BASE" "host B" design/b.md)

  run_guard "$b1" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"version conflict on v0.2.0"* ]]
  [[ "$output" == *"$a1"* ]]
  [[ "$output" == *"$b1"* ]]
}

@test "passes: commits after the release keep the same version" {
  local b1 b2
  b1=$(bump_020_from "$BASE" "host B" design/b.md)
  publish "$b1"
  origin_tag v0.2.0 "$b1"
  echo "# readme v2" > README.md
  git commit -q -am "docs after release"
  echo "# readme v3" > README.md
  git commit -q -am "more docs after release"
  b2=$(git rev-parse HEAD)

  run_guard "$b2" "$b1"
  [ "$status" -eq 0 ]
}

@test "passes: annotated tag on origin is compared by its peeled commit" {
  local b1 b2
  b1=$(bump_020_from "$BASE" "host B" design/b.md)
  publish "$b1"
  origin_tag v0.2.0 "$b1" annotated
  echo "# readme v2" > README.md
  git commit -q -am "docs after release"
  b2=$(git rev-parse HEAD)

  run_guard "$b2" "$b1"
  [ "$status" -eq 0 ]
}

@test "blocks: annotated tag on origin peeled to another host's release" {
  local a1 b1
  a1=$(bump_020_from "$BASE" "host A" design/a.md)
  origin_tag v0.2.0 "$a1" annotated
  b1=$(bump_020_from "$BASE" "host B" design/b.md)

  run_guard "$b1" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"version conflict on v0.2.0"* ]]
}

@test "blocks: merged divergent same-version bumps" {
  local a1 b1 m
  a1=$(bump_020_from "$BASE" "host A" design/a.md)
  publish "$a1"
  origin_tag v0.2.0 "$a1"
  b1=$(bump_020_from "$BASE" "host B" design/b.md)
  git merge -q --no-edit "$a1"
  m=$(git rev-parse HEAD)

  run_guard "$m" "$a1"
  [ "$status" -eq 1 ]
  [[ "$output" == *"version conflict on v0.2.0"* ]]
  [[ "$output" == *"$b1"* ]]
}

@test "passes: the merge commit that first carries the version is the release" {
  local b1 m
  b1=$(bump_020_from "$BASE" "host B" design/b.md)
  git checkout -q master
  git merge -q --no-ff --no-edit "$b1"
  m=$(git rev-parse HEAD)
  origin_tag v0.2.0 "$m" annotated

  run_guard "$m" "$BASE"
  [ "$status" -eq 0 ]
}

@test "passes: merge pull of another host's release without a local bump" {
  local a1 a2 b1 m
  a1=$(bump_020_from "$BASE" "host A" design/a.md)
  origin_tag v0.2.0 "$a1" annotated
  echo "host A docs" > design/a2.md
  git add -A
  git commit -q -m "docs after release"
  a2=$(git rev-parse HEAD)
  publish "$a2"
  git checkout -q master
  echo "host B docs" > README.md
  git add -A
  git commit -q -m "local docs"
  git merge -q --no-edit "$a2"
  m=$(git rev-parse HEAD)

  run_guard "$m" "$a2"
  [ "$status" -eq 0 ]
}

@test "blocks: the two manifests disagree on the pushed tip" {
  set_version "0.2.0" "0.2.1"
  git commit -q -am "half bump"
  local head; head=$(git rev-parse HEAD)

  run_guard "$head" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"manifests disagree"* ]]
}

@test "blocks with a clear message: origin unreachable" {
  echo "# readme v2" > README.md
  git commit -q -am "docs only"
  local head; head=$(git rev-parse HEAD)
  git remote set-url origin "$TEST_DIR/missing.git"

  run_guard "$head" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"cannot reach 'origin'"* ]]
}

@test "blocks within the deadline: origin hangs" {
  echo "# readme v2" > README.md
  git commit -q -am "docs only"
  local head; head=$(git rev-parse HEAD)
  git remote set-url origin "ssh://example.invalid/repo.git"
  local start; start=$(date +%s)

  GIT_SSH_COMMAND="sleep 30" VERSION_GUARD_LS_REMOTE_TIMEOUT=1 run_guard "$head" "$BASE"
  [ "$status" -eq 1 ]
  [[ "$output" == *"cannot reach 'origin'"* ]]
  [ $(( $(date +%s) - start )) -lt 10 ]
}
