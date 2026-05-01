#!/usr/bin/env bats
# Unit tests for PreToolUse hooks in .claude/settings.json

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
SETTINGS="$PROJECT_ROOT/.claude/settings.json"

setup() {
  TEST_DIR=$(mktemp -d)

  # Extract each hook command from settings.json into executable scripts.
  # Bash hooks are at .hooks.PreToolUse[0].hooks[], Edit/Write at [1].hooks[]

  # 1a. commit-msg-guard (git commit) — Bash hooks[0]
  jq -r '.hooks.PreToolUse[0].hooks[0].command' "$SETTINGS" > "$TEST_DIR/commit-msg-guard.sh"

  # 1b. commit-msg-guard (gh pr create) — Bash hooks[1]
  jq -r '.hooks.PreToolUse[0].hooks[1].command' "$SETTINGS" > "$TEST_DIR/commit-msg-guard-pr.sh"

  # 2. notes-guard — Bash hooks[2]
  jq -r '.hooks.PreToolUse[0].hooks[2].command' "$SETTINGS" > "$TEST_DIR/notes-guard.sh"

  # 3a. naming-guard (backlog task create) — Bash hooks[3]
  # Fix: replace <<< with printf pipe for POSIX sh compatibility
  jq -r '.hooks.PreToolUse[0].hooks[3].command' "$SETTINGS" \
    | python3 -c "import sys; print(sys.stdin.read().replace('<<< \"\$title\"', '< <(printf \"%s\" \"\$title\")'))" \
    > "$TEST_DIR/naming-guard-create.sh"

  # 3b. naming-guard (git checkout -b) — Bash hooks[4]
  jq -r '.hooks.PreToolUse[0].hooks[4].command' "$SETTINGS" \
    | python3 -c "import sys; print(sys.stdin.read().replace('<<< \"\$branch\"', '< <(printf \"%s\" \"\$branch\")'))" \
    > "$TEST_DIR/naming-guard-branch.sh"

  # 4. commit-prefix-guard — Bash hooks[5]
  jq -r '.hooks.PreToolUse[0].hooks[5].command' "$SETTINGS" > "$TEST_DIR/commit-prefix-guard.sh"

  # 5. task-file-guard — Edit/Write hooks[0]
  jq -r '.hooks.PreToolUse[1].hooks[0].command' "$SETTINGS" > "$TEST_DIR/task-file-guard.sh"

  # 6. master-branch-guard — Edit/Write hooks[1]
  jq -r '.hooks.PreToolUse[1].hooks[1].command' "$SETTINGS" > "$TEST_DIR/master-branch-guard.sh"
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

# Helper: run a hook script with JSON piped to stdin
run_hook() {
  local script="$1"
  local json="$2"
  echo "$json" | bash "$script" 2>/dev/null
}

# ===========================================================================
# 1. commit-msg-guard (git commit)
# ===========================================================================

@test "commit-msg-guard: blocks Co-Authored-By in git commit" {
  run run_hook "$TEST_DIR/commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"fix: stuff\nCo-Authored-By: someone\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"forbidden trailer"* ]]
}

@test "commit-msg-guard: blocks co-authored-by case-insensitive" {
  run run_hook "$TEST_DIR/commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"fix: stuff\nco-authored-by: someone\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard: blocks Generated with Claude Code" {
  run run_hook "$TEST_DIR/commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"fix: stuff\nGenerated with Claude Code\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard: blocks ## Test plan heading" {
  run run_hook "$TEST_DIR/commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"fix: stuff\n## Test plan\n- step 1\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard: allows clean commit message" {
  run run_hook "$TEST_DIR/commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"task-42: fix the widget\""}}'
  [[ -z "$output" ]]
}

@test "commit-msg-guard: ignores non-git-commit commands" {
  run run_hook "$TEST_DIR/commit-msg-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"echo Co-Authored-By in a string"}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 1b. commit-msg-guard (gh pr create)
# ===========================================================================

@test "commit-msg-guard-pr: blocks Co-Authored-By in gh pr create" {
  run run_hook "$TEST_DIR/commit-msg-guard-pr.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"gh pr create --title \"fix\" --body \"stuff\nCo-Authored-By: x\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard-pr: allows clean pr create" {
  run run_hook "$TEST_DIR/commit-msg-guard-pr.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"gh pr create --title \"fix\" --body \"clean body\""}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 2. notes-guard
# ===========================================================================

@test "notes-guard: blocks --notes with space" {
  run run_hook "$TEST_DIR/notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 --notes \"new notes\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"--notes overwrites"* ]]
}

@test "notes-guard: blocks --notes= syntax" {
  run run_hook "$TEST_DIR/notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 --notes=\"new notes\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "notes-guard: blocks --notes at end of command (TASK-67 regression)" {
  run run_hook "$TEST_DIR/notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 --notes"}}'
  [[ "$output" == *"deny"* ]]
}

@test "notes-guard: allows --append-notes" {
  run run_hook "$TEST_DIR/notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 --append-notes \"extra info\""}}'
  [[ -z "$output" ]]
}

@test "notes-guard: ignores non-backlog commands" {
  run run_hook "$TEST_DIR/notes-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"echo --notes something"}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 3. task-file-guard
# ===========================================================================

@test "task-file-guard: blocks Edit to task file" {
  run run_hook "$TEST_DIR/task-file-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"backlog/tasks/task-42.md"}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"do not edit task files"* ]]
}

@test "task-file-guard: blocks Write to task file with absolute path" {
  run run_hook "$TEST_DIR/task-file-guard.sh" \
    '{"tool_name":"Write","tool_input":{"file_path":"/workspace/backlog/tasks/task-99-something.md"}}'
  [[ "$output" == *"deny"* ]]
}

@test "task-file-guard: allows edit to .ralph-status.json" {
  run run_hook "$TEST_DIR/task-file-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"backlog/.ralph-status.json"}}'
  [[ -z "$output" ]]
}

@test "task-file-guard: allows edit to non-task paths" {
  run run_hook "$TEST_DIR/task-file-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"src/main.js"}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 4. master-branch-guard
# ===========================================================================

setup_git_repo() {
  git init "$TEST_DIR/repo" >/dev/null 2>&1
  git -C "$TEST_DIR/repo" config user.email "test@test.com"
  git -C "$TEST_DIR/repo" config user.name "Test"
  git -C "$TEST_DIR/repo" commit --allow-empty -m "init" >/dev/null 2>&1
}

run_hook_in_repo() {
  local script="$1"
  local json="$2"
  echo "$json" | bash -c "cd '$TEST_DIR/repo' && bash '$script'" 2>/dev/null
}

@test "master-branch-guard: blocks edit on master to non-allowlisted path" {
  setup_git_repo
  run run_hook_in_repo "$TEST_DIR/master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"README.md"}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"no active task branch"* ]]
}

@test "master-branch-guard: allows .claude/ path on master" {
  setup_git_repo
  run run_hook_in_repo "$TEST_DIR/master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".claude/settings.json"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows .gitignore on master" {
  setup_git_repo
  run run_hook_in_repo "$TEST_DIR/master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".gitignore"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows edit on task branch" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-42-test >/dev/null 2>&1
  run run_hook_in_repo "$TEST_DIR/master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"README.md"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: handles detached HEAD gracefully" {
  setup_git_repo
  local hash
  hash=$(git -C "$TEST_DIR/repo" rev-parse HEAD)
  git -C "$TEST_DIR/repo" checkout "$hash" >/dev/null 2>&1
  run run_hook_in_repo "$TEST_DIR/master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":"ralph.sh"}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 5. naming-guard
# ===========================================================================

@test "naming-guard: blocks non-ASCII title in backlog task create (TASK-67 regression)" {
  run run_hook "$TEST_DIR/naming-guard-create.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task create \"Привет мир\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"ASCII English"* ]]
}

@test "naming-guard: allows ASCII title in backlog task create" {
  run run_hook "$TEST_DIR/naming-guard-create.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task create \"Add login feature\" -d \"Описание на русском\""}}'
  [[ -z "$output" ]]
}

@test "naming-guard: blocks non-ASCII branch name in git checkout -b (TASK-67 regression)" {
  run run_hook "$TEST_DIR/naming-guard-branch.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git checkout -b задача-42"}}'
  [[ "$output" == *"deny"* ]]
}

@test "naming-guard: allows ASCII branch name in git checkout -b" {
  run run_hook "$TEST_DIR/naming-guard-branch.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git checkout -b task-42-new-feature"}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 6. commit-prefix-guard
# ===========================================================================

@test "commit-prefix-guard: blocks commit without task prefix on task branch" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-99-feature >/dev/null 2>&1
  run run_hook_in_repo "$TEST_DIR/commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"foo bar\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"task-99"* ]]
}

@test "commit-prefix-guard: allows correctly prefixed commit on task branch" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-99-feature >/dev/null 2>&1
  run run_hook_in_repo "$TEST_DIR/commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"task-99: fix the widget\""}}'
  [[ -z "$output" ]]
}

@test "commit-prefix-guard: allows merge commits on task branch" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-99-feature >/dev/null 2>&1
  run run_hook_in_repo "$TEST_DIR/commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"Merge branch master into task-99\""}}'
  [[ -z "$output" ]]
}

@test "commit-prefix-guard: allows any commit on master" {
  setup_git_repo
  run run_hook_in_repo "$TEST_DIR/commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"random message\""}}'
  [[ -z "$output" ]]
}
