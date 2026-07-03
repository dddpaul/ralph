#!/usr/bin/env bats
# Unit tests for plugins/ralph/skills/ralph-init/templates/git-hooks/commit-msg
#
# Regression: when commit.verbose=true (or `git commit -v`), git appends the
# staged diff below a scissor line. The hook must scan only the author-written
# body above the scissor, otherwise the diff trips the guard on the very first
# commit of a ralph-init scaffold (the diff contains the hook's own grep regex).

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
HOOK="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/git-hooks/commit-msg"

# Forbidden literals built at runtime so the bats file itself is not flagged
# by the surrounding PreToolUse / commit-msg guards.
CA="Co-Author"; CA="${CA}ed-By"
GEN="Generated with Claude Code"
TP="## Test plan"

setup() {
  TEST_DIR=$(mktemp -d)
  # Run in a tmp git repo so the hook's `[ -e .git/MERGE_MSG ]` check is meaningful.
  cd "$TEST_DIR"
  git init -q
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

# ---------------------------------------------------------------------------
# Positive: scissor-bug regression
# ---------------------------------------------------------------------------

@test "commit-msg: passes when forbidden text appears only below the scissor line" {
  cat > msg <<EOF
Initial commit

# ------------------------ >8 ------------------------
# scissor section — git strips below this, but the hook reads it
diff --git a/.claude/hooks/commit-msg-guard.sh b/.claude/hooks/commit-msg-guard.sh
+   if echo "\$cmd" | grep -qiE '${CA}|${GEN}' ||
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# Negative: Co-Authored-By in author body
# ---------------------------------------------------------------------------

@test "commit-msg: blocks Co-Authored-By in author body (no scissor)" {
  cat > msg <<EOF
fix: stuff

${CA}: someone <a@b.c>
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 1 ]
  [[ "$output" == *"BLOCKED"* ]]
}

@test "commit-msg: blocks Co-Authored-By above scissor even when below is clean" {
  cat > msg <<EOF
fix: stuff

${CA}: someone <a@b.c>

# ------------------------ >8 ------------------------
# (clean diff would go here)
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 1 ]
}

# ---------------------------------------------------------------------------
# Negative: Generated-with trailer in author body
# ---------------------------------------------------------------------------

@test "commit-msg: blocks Generated-with-Claude-Code in author body" {
  cat > msg <<EOF
chore: stuff

${GEN}
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 1 ]
}

# ---------------------------------------------------------------------------
# Negative: Test plan heading in author body
# ---------------------------------------------------------------------------

@test "commit-msg: blocks ## Test plan heading in author body" {
  cat > msg <<EOF
feat: stuff

${TP}
- step 1
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 1 ]
}

# ---------------------------------------------------------------------------
# Sanity: clean message passes
# ---------------------------------------------------------------------------

@test "commit-msg: clean message with no forbidden tokens passes" {
  cat > msg <<EOF
fix: a normal commit body

with multiple lines and no trailers.
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# Sanity: merge commit bypass still works
# ---------------------------------------------------------------------------

@test "commit-msg: skips check when .git/MERGE_MSG present (merge commit)" {
  touch .git/MERGE_MSG
  cat > msg <<EOF
Merge branch 'foo'

${CA}: noisy
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# Sanity: fixup/squash messages bypass
# ---------------------------------------------------------------------------

@test "commit-msg: skips fixup! prefixed messages" {
  cat > msg <<EOF
fixup! prior commit

${CA}: ignored
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 0 ]
}

@test "commit-msg: skips squash! prefixed messages" {
  cat > msg <<EOF
squash! prior commit

${CA}: ignored
EOF
  run bash "$HOOK" msg
  [ "$status" -eq 0 ]
}
