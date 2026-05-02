#!/usr/bin/env bats
# Unit tests for PreToolUse hook scripts in .claude/hooks/

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"

setup() {
  TEST_DIR=$(mktemp -d)
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

# Helper: run a hook script with JSON piped to stdin
run_hook() {
  local script="$HOOKS_DIR/$1"
  local json="$2"
  echo "$json" | bash "$script" 2>/dev/null
}

# ===========================================================================
# 1. commit-msg-guard (git commit)
# ===========================================================================

@test "commit-msg-guard: blocks Co-Authored-By in git commit" {
  run run_hook "commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"fix: stuff\nCo-Authored-By: someone\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"forbidden trailer"* ]]
}

@test "commit-msg-guard: blocks co-authored-by case-insensitive" {
  run run_hook "commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"fix: stuff\nco-authored-by: someone\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard: blocks Generated with Claude Code" {
  run run_hook "commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"fix: stuff\nGenerated with Claude Code\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard: blocks ## Test plan heading" {
  run run_hook "commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"fix: stuff\n## Test plan\n- step 1\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard: allows clean commit message" {
  run run_hook "commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"task-42: fix the widget\""}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 1b. commit-msg-guard (gh pr create)
# ===========================================================================

@test "commit-msg-guard-pr: blocks Co-Authored-By in gh pr create" {
  run run_hook "commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"gh pr create --title \"fix\" --body \"stuff\nCo-Authored-By: x\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard-pr: allows clean pr create" {
  run run_hook "commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"gh pr create --title \"fix\" --body \"clean body\""}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 2. notes-guard
# ===========================================================================

@test "notes-guard: blocks --notes with space" {
  run run_hook "notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 --notes \"new notes\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"--notes overwrites"* ]]
}

@test "notes-guard: blocks --notes= syntax" {
  run run_hook "notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 --notes=\"new notes\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "notes-guard: blocks --notes at end of command (TASK-67 regression)" {
  run run_hook "notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 --notes"}}'
  [[ "$output" == *"deny"* ]]
}

@test "notes-guard: allows --append-notes" {
  run run_hook "notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 --append-notes \"extra info\""}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 3. master-branch-guard
# ===========================================================================

setup_git_repo() {
  git init "$TEST_DIR/repo" >/dev/null 2>&1
  git -C "$TEST_DIR/repo" config user.email "test@test.com"
  git -C "$TEST_DIR/repo" config user.name "Test"
  git -C "$TEST_DIR/repo" commit --allow-empty -m "init" >/dev/null 2>&1
}

run_hook_in_repo() {
  local script="$HOOKS_DIR/$1"
  local json="$2"
  echo "$json" | bash -c "cd '$TEST_DIR/repo' && bash '$script'" 2>/dev/null
}

@test "master-branch-guard: blocks edit on master to non-allowlisted path" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"README.md"}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"no active task branch"* ]]
}

@test "master-branch-guard: allows .claude/ path on master" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".claude/settings.json"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows .gitignore on master" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".gitignore"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows edit on task branch" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-42-test >/dev/null 2>&1
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"README.md"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: handles detached HEAD gracefully" {
  setup_git_repo
  local hash
  hash=$(git -C "$TEST_DIR/repo" rev-parse HEAD)
  git -C "$TEST_DIR/repo" checkout "$hash" >/dev/null 2>&1
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"ralph.sh"}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 4. naming-guard
# ===========================================================================

@test "naming-guard: blocks non-ASCII title in backlog task create (TASK-67 regression)" {
  run run_hook "naming-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task create \"Привет мир\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"ASCII English"* ]]
}

@test "naming-guard: allows ASCII title in backlog task create" {
  run run_hook "naming-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task create \"Add login feature\" -d \"Описание на русском\""}}'
  [[ -z "$output" ]]
}

@test "naming-guard: blocks non-ASCII branch name in git checkout -b (TASK-67 regression)" {
  run run_hook "naming-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git checkout -b задача-42"}}'
  [[ "$output" == *"deny"* ]]
}

@test "naming-guard: allows ASCII branch name in git checkout -b" {
  run run_hook "naming-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git checkout -b task-42-new-feature"}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 5. commit-prefix-guard
# ===========================================================================

@test "commit-prefix-guard: blocks commit without task prefix on task branch" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-99-feature >/dev/null 2>&1
  run run_hook_in_repo "commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"foo bar\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"task-99"* ]]
}

@test "commit-prefix-guard: allows correctly prefixed commit on task branch" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-99-feature >/dev/null 2>&1
  run run_hook_in_repo "commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"task-99: fix the widget\""}}'
  [[ -z "$output" ]]
}

@test "commit-prefix-guard: allows merge commits on task branch" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-99-feature >/dev/null 2>&1
  run run_hook_in_repo "commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"Merge branch master into task-99\""}}'
  [[ -z "$output" ]]
}

@test "commit-prefix-guard: allows any commit on master" {
  setup_git_repo
  run run_hook_in_repo "commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"random message\""}}'
  [[ -z "$output" ]]
}
