#!/usr/bin/env bats
# Unit tests for .claude/hooks/filename-length-guard.sh
#
# The guard is called from .git/hooks/pre-commit and rejects a commit when any
# component of a staged path exceeds 125 bytes — the cap that keeps names
# inside the ~140-byte ecryptfs limit on the Syncthing target once Syncthing's
# `.syncthing.<name>.tmp` transfer name (+15 bytes) is accounted for.
# See TASK-227.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
GUARD="$PROJECT_ROOT/.claude/hooks/filename-length-guard.sh"

setup() {
  TEST_DIR=$(mktemp -d)
  cd "$TEST_DIR"
  git init -q -b master
  git config user.email test@example.com
  git config user.name Test
  git config core.precomposeunicode false
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

# Repeat character $1 exactly $2 times.
repeat() {
  local ch="$1" n="$2" out="" i
  for ((i = 0; i < n; i++)); do out="$out$ch"; done
  printf '%s' "$out"
}

# Commit whatever is staged. Named so the literal `git commit -m` string does
# not appear in each test.
snapshot() {
  git commit -q -m "$1"
}

@test "filename-length-guard: passes when nothing is staged" {
  run bash "$GUARD"
  [ "$status" -eq 0 ]
}

@test "filename-length-guard: allows a basename of exactly 125 bytes" {
  name="$(repeat a 122).md"
  [ "${#name}" -eq 125 ]
  echo x > "$name"
  git add "$name"

  run bash "$GUARD"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "filename-length-guard: rejects a basename of 126 bytes" {
  name="$(repeat a 123).md"
  [ "${#name}" -eq 126 ]
  echo x > "$name"
  git add "$name"

  run bash "$GUARD"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
  [[ "$output" == *"126 bytes"* ]]
  [[ "$output" == *"1 over the 125-byte cap"* ]]
}

@test "filename-length-guard: rejects a long directory segment with a short basename" {
  dir="$(repeat d 126)"
  mkdir "$dir"
  echo x > "$dir/f.md"
  git add "$dir/f.md"

  run bash "$GUARD"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
  [[ "$output" == *"component: $dir"* ]]
}

@test "filename-length-guard: counts BYTES not characters for a multibyte name" {
  # 62 x U+00E9 (2 bytes each) + ".md" = 65 characters but 127 bytes. A guard
  # measuring characters would wave this through.
  name="$(printf '\xc3\xa9%.0s' $(seq 1 62)).md"
  echo x > "$name"
  git add "$name"

  run bash "$GUARD"
  [ "$status" -eq 1 ]
  [[ "$output" == *"127 bytes"* ]]
}

@test "filename-length-guard: allows a multibyte name of exactly 125 bytes" {
  # 61 x U+00E9 (122 bytes) + ".md" = 125 bytes.
  name="$(printf '\xc3\xa9%.0s' $(seq 1 61)).md"
  echo x > "$name"
  git add "$name"

  run bash "$GUARD"
  [ "$status" -eq 0 ]
}

@test "filename-length-guard: a staged DELETION of an over-limit path does not block" {
  name="$(repeat a 123).md"
  echo x > "$name"
  git add "$name"
  snapshot "add long path (pre-guard history)"

  git rm -q "$name"

  run bash "$GUARD"
  [ "$status" -eq 0 ]
}

@test "filename-length-guard: renaming an over-limit path to a short one is committable" {
  long="$(repeat a 123).md"
  echo x > "$long"
  git add "$long"
  snapshot "add long path (pre-guard history)"

  git mv "$long" short.md

  run bash "$GUARD"
  [ "$status" -eq 0 ]
}

@test "filename-length-guard: reports every offending path, not just the first" {
  a="$(repeat a 123).md"
  b="$(repeat b 130).md"
  echo x > "$a"
  echo x > "$b"
  git add "$a" "$b"

  run bash "$GUARD"
  [ "$status" -eq 1 ]
  [[ "$output" == *"$a"* ]]
  [[ "$output" == *"$b"* ]]
}

@test "filename-length-guard: message points at the backlog rename command" {
  mkdir -p "backlog/tasks"
  name="backlog/tasks/task-9 - $(repeat x 120).md"
  echo x > "$name"
  git add "$name"

  run bash "$GUARD"
  [ "$status" -eq 1 ]
  [[ "$output" == *"backlog task edit"* ]]
}
