#!/usr/bin/env bats
# Unit tests for skills/ralph-init/templates/git-hooks/pre-commit
#
# The hook rejects a commit when a staged path's Unicode-normalized (NFC) form
# collides with an existing tree path that differs only by normalization (NFD vs
# NFC). See TASK-136 for the downstream incident.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
HOOK="$PROJECT_ROOT/skills/ralph-init/templates/git-hooks/pre-commit"

# Russian й in NFC (U+0439, bytes d0 b9) and NFD (U+0438 U+0306, bytes d0 b8 cc 86).
NFC_NAME=$(python3 -c 'import unicodedata, sys; sys.stdout.write(unicodedata.normalize("NFC", "й.md"))')
NFD_NAME=$(python3 -c 'import unicodedata, sys; sys.stdout.write(unicodedata.normalize("NFD", "й.md"))')

setup() {
  TEST_DIR=$(mktemp -d)
  cd "$TEST_DIR"
  git init -q -b master
  git config user.email test@example.com
  git config user.name Test
  # Force Linux semantics so the hook sees the byte forms we wrote, regardless
  # of host platform — macOS would otherwise pre-compose NFD to NFC at git layer.
  git config core.precomposeunicode false
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

@test "pre-commit: passes when staging an unrelated clean path" {
  echo a > existing.md
  git add existing.md
  git commit -q -m "init"

  echo b > unrelated.md
  git add unrelated.md

  run bash "$HOOK"
  [ "$status" -eq 0 ]
}

@test "pre-commit: blocks staging NFD form when NFC exists at HEAD" {
  echo nfc > "$NFC_NAME"
  git add "$NFC_NAME"
  git commit -q -m "add NFC form"

  echo nfd > "$NFD_NAME"
  git add "$NFD_NAME"

  run bash "$HOOK"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "pre-commit: blocks staging NFC form when NFD exists at HEAD" {
  echo nfd > "$NFD_NAME"
  git add "$NFD_NAME"
  git commit -q -m "add NFD form"

  echo nfc > "$NFC_NAME"
  git add "$NFC_NAME"

  run bash "$HOOK"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "pre-commit: passes on empty repo (no HEAD)" {
  echo a > first.md
  git add first.md

  run bash "$HOOK"
  [ "$status" -eq 0 ]
}

@test "pre-commit: passes when nothing staged" {
  echo a > existing.md
  git add existing.md
  git commit -q -m "init"

  run bash "$HOOK"
  [ "$status" -eq 0 ]
}

@test "pre-commit: passes when staging a modification (same byte path as HEAD)" {
  echo a > "$NFC_NAME"
  git add "$NFC_NAME"
  git commit -q -m "init"

  echo b > "$NFC_NAME"
  git add "$NFC_NAME"

  run bash "$HOOK"
  [ "$status" -eq 0 ]
}
