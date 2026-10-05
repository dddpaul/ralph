#!/usr/bin/env bats
# Unit tests for plugins/ralph/skills/ralph-init/templates/git-hooks/pre-commit
#
# The hook rejects a commit when a staged path's Unicode-normalized (NFC) form
# collides with an existing tree path that differs only by normalization (NFD vs
# NFC). See TASK-136 for the downstream incident.
#
# It also delegates to .claude/hooks/filename-length-guard.sh when that script is
# present and executable — see TASK-227.

load '../helpers/common'
HOOK="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/git-hooks/pre-commit"
LENGTH_GUARD="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/claude/hooks/filename-length-guard.sh"

# Russian й in NFC (U+0439, bytes d0 b9) and NFD (U+0438 U+0306, bytes d0 b8 cc 86).
NFC_NAME=$(python3 -c 'import unicodedata, sys; sys.stdout.write(unicodedata.normalize("NFC", "й.md"))')
NFD_NAME=$(python3 -c 'import unicodedata, sys; sys.stdout.write(unicodedata.normalize("NFD", "й.md"))')

# Stage a path through git plumbing: no file is ever written to the working
# tree. The NFC/NFD pair has to exist as two distinct index entries, and a
# normalization-collapsing volume (macOS APFS) merges two such files into one —
# so building the fixture on disk is impossible there, while plumbing works
# everywhere.
stage_plumbed() {
  local blob
  blob=$(printf '%s\n' "$2" | git hash-object -w --stdin)
  git update-index --add --cacheinfo "100644,$blob,$1"
}

setup() {
  TEST_DIR="$(make_temp_dir)"
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
  stage_plumbed "$NFC_NAME" nfc
  git commit -q -m "add NFC form"

  stage_plumbed "$NFD_NAME" nfd

  run bash "$HOOK"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "pre-commit: blocks staging NFC form when NFD exists at HEAD" {
  stage_plumbed "$NFD_NAME" nfd
  git commit -q -m "add NFD form"

  stage_plumbed "$NFC_NAME" nfc

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

# ===========================================================================
# filename-length-guard delegation (TASK-227)
# ===========================================================================

# Install the length guard into the temp repo at the path the hook resolves.
install_length_guard() {
  mkdir -p .claude/hooks
  cp "$LENGTH_GUARD" .claude/hooks/filename-length-guard.sh
  chmod +x .claude/hooks/filename-length-guard.sh
}

# A basename of 126 bytes — one over the cap.
stage_over_limit_path() {
  local name="" i
  for ((i = 0; i < 123; i++)); do name="${name}a"; done
  name="${name}.md"
  echo x > "$name"
  git add "$name"
}

@test "pre-commit: blocks an over-limit staged path when the length guard is executable" {
  install_length_guard
  stage_over_limit_path

  run bash "$HOOK"
  [ "$status" -eq 1 ]
  [[ "$output" == *"125-byte"* ]]
}

@test "pre-commit: skips silently when the length guard is not executable" {
  install_length_guard
  chmod -x .claude/hooks/filename-length-guard.sh
  stage_over_limit_path

  run bash "$HOOK"
  [ "$status" -eq 0 ]
  [[ "$output" != *"125-byte"* ]]
}

@test "pre-commit: skips silently when the length guard is absent" {
  stage_over_limit_path

  run bash "$HOOK"
  [ "$status" -eq 0 ]
  [[ "$output" != *"125-byte"* ]]
}

@test "pre-commit: allows an at-limit staged path when the length guard is executable" {
  install_length_guard
  name=""
  for ((i = 0; i < 122; i++)); do name="${name}a"; done
  name="${name}.md"
  [ "${#name}" -eq 125 ]
  echo x > "$name"
  git add "$name"

  run bash "$HOOK"
  [ "$status" -eq 0 ]
}

# ===========================================================================
# normalizer selection by execution (TASK-242)
# ===========================================================================
#
# The hook used to pick its NFC normalizer with `command -v python3`. A
# devcontainer built from the docs/python templates carried a python3 first in
# PATH that could not start at all (an interpreter copied from an official
# python:* image whose glibc was newer than the base image's), so every to_nfc
# call exited non-zero and `set -euo pipefail` aborted the hook — i.e. every
# commit inside the container was rejected. The host cannot show the defect:
# macOS BSD iconv ships utf-8-mac, so the first branch wins and python3 is
# never reached. These tests therefore assert the outcome (blocked / not
# aborted) rather than which branch ran.

# A python3 first in PATH that exits non-zero on any invocation.
install_broken_python3() {
  mkdir -p stub
  cat > stub/python3 <<'STUB'
#!/bin/sh
echo "python3: /lib/libm.so.6: version \`GLIBC_2.38' not found" >&2
exit 1
STUB
  chmod +x stub/python3
}

@test "pre-commit: still BLOCKS an NFD duplicate when python3 in PATH cannot start" {
  stage_plumbed "$NFC_NAME" nfc
  git -c core.hooksPath=/dev/null commit -q -m "add NFC form"
  stage_plumbed "$NFD_NAME" nfd
  install_broken_python3

  run env PATH="$PWD/stub:$PATH" bash "$HOOK"
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "pre-commit: a broken python3 in PATH does not abort a clean commit" {
  stage_plumbed existing.md a
  git -c core.hooksPath=/dev/null commit -q -m "init"
  stage_plumbed unrelated.md b
  install_broken_python3

  run env PATH="$PWD/stub:$PATH" bash "$HOOK"
  [ "$status" -eq 0 ]
  [[ "$output" != *"GLIBC"* ]]
}

@test "pre-commit: the normalizer is chosen by running the candidate, not by lookup" {
  # Pins the mechanism so the `command -v` selection cannot come back through a
  # later edit while both behavioural tests above still pass on a macOS host
  # (where the iconv branch wins and no python is ever consulted).
  run grep -n -E "command -v python3.*then" "$HOOK"
  [ "$status" -ne 0 ]
  grep -q -- '-c .import unicodedata.' "$HOOK"
}
