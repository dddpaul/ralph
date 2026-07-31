#!/usr/bin/env bats
# Unit tests for .claude/hooks/version-bump-guard.sh — the pre-push guard that
# blocks a master push which changes shipped plugin files without a strictly
# greater plugin version (so `/plugin update` rebuilds the consumer cache).
# See TASK-214.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
HOOK="$PROJECT_ROOT/.claude/hooks/version-bump-guard.sh"
MANIFEST="plugins/ralph/.claude-plugin/plugin.json"
SHIPPED="plugins/ralph/skills/ralph-run/SKILL.md"
ZERO="0000000000000000000000000000000000000000"

# Write the plugin manifest at $MANIFEST with the given version.
set_version() {
  mkdir -p "$(dirname "$MANIFEST")"
  printf '{\n  "name": "ralph",\n  "version": "%s"\n}\n' "$1" > "$MANIFEST"
}

# Feed one master ref-update line to the guard: <local> <remote>.
run_guard() { # $1=local_sha $2=remote_sha [$3=remote_ref]
  local ref="${3:-refs/heads/master}"
  run bash "$HOOK" <<EOF
refs/heads/master $1 $ref $2
EOF
}

setup() {
  TEST_DIR=$(mktemp -d)
  cd "$TEST_DIR"
  git init -q -b master
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
