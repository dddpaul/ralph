#!/usr/bin/env bats
# Unit tests for PreToolUse hook scripts in .claude/hooks/

load '../helpers/common'
HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"

setup() {
  TEST_DIR="$(make_temp_dir)"
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
# 1c. commit-msg-guard gate: only a real commit or pr create (TASK-281)
# ===========================================================================

# Helper: a Bash tool_input JSON for an arbitrary (multi-line) command
cmd_json() {
  jq -nc --arg c "$1" '{tool_name: "Bash", tool_input: {command: $c}}'
}

@test "commit-msg-guard: ignores backlog task create naming the trailers (TASK-281)" {
  run run_hook "commit-msg-guard.sh" "$(cmd_json 'backlog task create "Ban trailers" -d "Forbid Co-Authored-By, Generated with Claude Code and ## Test plan in git commit messages"')"
  [ "$status" -eq 0 ]
  [[ -z "$output" ]]
}

@test "commit-msg-guard: ignores notes quoting a commit with a trailer (TASK-281)" {
  run run_hook "commit-msg-guard.sh" "$(cmd_json 'backlog task edit 7 --append-notes "Denied:
git commit -m \"x

Co-Authored-By: a\""')"
  [ "$status" -eq 0 ]
  [[ -z "$output" ]]
}

@test "commit-msg-guard: ignores a heredoc script mentioning commit and trailer (TASK-281)" {
  run run_hook "commit-msg-guard.sh" "$(cmd_json "python3 - <<'PY'
print('git commit -m \"Co-Authored-By: x\"')
PY")"
  [ "$status" -eq 0 ]
  [[ -z "$output" ]]
}

@test "commit-msg-guard: blocks a trailer in a multi-line commit after another command (TASK-281)" {
  run run_hook "commit-msg-guard.sh" "$(cmd_json 'git add -u && git commit -m "task-1: fix

Co-Authored-By: someone"')"
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard: blocks a Test plan heading in a heredoc commit message (TASK-281)" {
  run run_hook "commit-msg-guard.sh" "$(cmd_json "cat <<'MSG' | git commit -F -
task-1: fix

## Test plan
- run it
MSG")"
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard: blocks a trailer in a commit behind env (TASK-281)" {
  run run_hook "commit-msg-guard.sh" "$(cmd_json "env git commit -m 'x

Co-Authored-By: y'")"
  [[ "$output" == *"deny"* ]]
}

@test "commit-msg-guard and commit-prefix-guard share an identical lexer (TASK-281)" {
  local a b
  a=$(sed -n '/^# >>> shared command lexer/,/^# <<< shared command lexer/p' "$HOOKS_DIR/commit-msg-guard.sh")
  b=$(sed -n '/^# >>> shared command lexer/,/^# <<< shared command lexer/p' "$HOOKS_DIR/commit-prefix-guard.sh")
  [[ -n "$a" ]]
  [[ "$a" == "$b" ]]
}

@test "commit guards use neither python3 nor a line-based sed extraction (TASK-281)" {
  ! grep -q 'python' "$HOOKS_DIR/commit-msg-guard.sh" "$HOOKS_DIR/commit-prefix-guard.sh"
  ! grep -q 'sed -n' "$HOOKS_DIR/commit-prefix-guard.sh"
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
  git init -b master "$TEST_DIR/repo" >/dev/null 2>&1
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

@test "master-branch-guard: allows .obsidian/ path on master" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".obsidian/app.json"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows .vscode/ path on master" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".vscode/settings.json"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows .idea/ path on master" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".idea/workspace.xml"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows .cursor/ path on master" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".cursor/settings.json"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows .zed/ path on master" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".zed/settings.json"}}'
  [[ -z "$output" ]]
}

@test "master-branch-guard: allows .fleet/ path on master" {
  setup_git_repo
  run run_hook_in_repo "master-branch-guard.sh" \
    '{"tool_name":"Edit","tool_input":{"file_path":".fleet/settings.json"}}'
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
# 4b. naming-guard — title length (TASK-227)
#
# Artifact filenames are derived from titles, so a title over 100 characters
# produces a filename that blows the 125-byte cap enforced at commit time by
# filename-length-guard.sh.
# ===========================================================================

# A title of exactly $1 ASCII characters.
title_of() {
  local n="$1" out="" i
  for ((i = 0; i < n; i++)); do out="${out}A"; done
  printf '%s' "$out"
}

hook_json() {
  printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"
}

@test "naming-guard: blocks a 101-char title in backlog task create" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog task create \\\"$(title_of 101)\\\"")"
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"101 chars, max 100"* ]]
}

@test "naming-guard: allows a title of exactly 100 chars in backlog task create" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog task create \\\"$(title_of 100)\\\"")"
  [[ -z "$output" ]]
}

@test "naming-guard: blocks a 101-char title in backlog task edit -t" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog task edit 42 -t \\\"$(title_of 101)\\\"")"
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"101 chars, max 100"* ]]
}

@test "naming-guard: blocks a 101-char title in backlog task edit --title" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog task edit 42 --title \\\"$(title_of 101)\\\"")"
  [[ "$output" == *"deny"* ]]
}

@test "naming-guard: allows a title of exactly 100 chars in backlog task edit -t" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog task edit 42 -t \\\"$(title_of 100)\\\"")"
  [[ -z "$output" ]]
}

@test "naming-guard: blocks non-ASCII title in backlog task edit -t" {
  run run_hook "naming-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog task edit 42 -t \"Привет мир\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"ASCII English"* ]]
}

@test "naming-guard: blocks a 101-char title in backlog doc create" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog doc create \\\"$(title_of 101)\\\"")"
  [[ "$output" == *"deny"* ]]
}

@test "naming-guard: blocks non-ASCII title in backlog doc create" {
  run run_hook "naming-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog doc create \"Привет мир\""}}'
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"ASCII English"* ]]
}

@test "naming-guard: blocks a 101-char title in backlog decision create" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog decision create \\\"$(title_of 101)\\\"")"
  [[ "$output" == *"deny"* ]]
}

@test "naming-guard: blocks non-ASCII title in backlog decision create" {
  run run_hook "naming-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog decision create \"Привет мир\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "naming-guard: blocks a 101-char title in backlog draft create" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog draft create \\\"$(title_of 101)\\\"")"
  [[ "$output" == *"deny"* ]]
}

@test "naming-guard: blocks non-ASCII title in backlog draft create" {
  run run_hook "naming-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"backlog draft create \"Привет мир\""}}'
  [[ "$output" == *"deny"* ]]
}

@test "naming-guard: does not treat a long --append-notes value as a title" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog task edit 42 --append-notes \\\"$(title_of 400)\\\"")"
  [[ -z "$output" ]]
}

@test "naming-guard: does not apply the length cap to branch names" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "git checkout -b task-42-$(title_of 200)")"
  [[ -z "$output" ]]
}

@test "naming-guard: checks each command separately in a multi-line invocation" {
  run run_hook "naming-guard.sh" \
    "$(hook_json "backlog task create \\\"Short one\\\"\\nbacklog task create \\\"$(title_of 101)\\\"")"
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"101 chars, max 100"* ]]
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

@test "commit-prefix-guard: ignores non-commit command on task branch (TASK-123 regression)" {
  setup_git_repo
  git -C "$TEST_DIR/repo" checkout -b task-99-feature >/dev/null 2>&1
  run run_hook_in_repo "commit-prefix-guard.sh" \
    '{"tool_name":"Bash","tool_input":{"command":"kill 1"}}'
  [[ -z "$output" ]]
}

# ===========================================================================
# 5b. commit-prefix-guard: command-position gate and multi-line extraction
#     (TASK-281)
# ===========================================================================

# Helper: run commit-prefix-guard on a task-99 branch for a command string
prefix_guard_on_task_branch() {
  [[ -d "$TEST_DIR/repo" ]] || {
    setup_git_repo
    git -C "$TEST_DIR/repo" checkout -b task-99-feature >/dev/null 2>&1
  }
  run run_hook_in_repo "commit-prefix-guard.sh" "$(cmd_json "$1")"
}

assert_denied() {
  [[ "$output" == *"deny"* ]]
  [[ "$output" == *"task-99"* ]]
}

assert_allowed() {
  [ "$status" -eq 0 ]
  [[ -z "$output" ]]
}

@test "commit-prefix-guard: allows a prefixed multi-line double-quoted -m" {
  prefix_guard_on_task_branch 'git commit -m "task-99: fix the widget

Longer body line."'
  assert_allowed
}

@test "commit-prefix-guard: allows a prefixed multi-line single-quoted -m" {
  prefix_guard_on_task_branch "git commit -m 'task-99: it'\\''s fixed

Body.'"
  assert_allowed
}

@test "commit-prefix-guard: blocks an unprefixed multi-line -m" {
  prefix_guard_on_task_branch 'git commit -m "fix the widget

task-99: is not the subject"'
  assert_denied
}

@test "commit-prefix-guard: blocks a wrongly prefixed single-line -m" {
  prefix_guard_on_task_branch 'git commit -m "task-98: fix the widget"'
  assert_denied
}

@test "commit-prefix-guard: blocks a wrongly prefixed multi-line -m" {
  prefix_guard_on_task_branch "git commit -m 'task-98: fix the widget

Body.'"
  assert_denied
}

@test "commit-prefix-guard: ignores notes quoting the commit phrase" {
  prefix_guard_on_task_branch 'backlog task edit 99 --append-notes "Run git commit -m \"foo\" then
git commit --amend"'
  assert_allowed
}

@test "commit-prefix-guard: ignores a heredoc script mentioning the commit phrase" {
  prefix_guard_on_task_branch "python3 - <<'PY'
import os
os.system('git commit -m foo')
PY"
  assert_allowed
}

@test "commit-prefix-guard: ignores git log whose argument is the word commit" {
  prefix_guard_on_task_branch 'git log --grep commit'
  assert_allowed
}

@test "commit-prefix-guard: --message= is checked" {
  prefix_guard_on_task_branch 'git commit --message="task-99: ok"'
  assert_allowed
  prefix_guard_on_task_branch 'git commit --message="not ok"'
  assert_denied
}

@test "commit-prefix-guard: -F and --file read the named file" {
  printf 'task-99: from a file\n\nBody.\n' > "$TEST_DIR/good.txt"
  printf 'no prefix\n' > "$TEST_DIR/bad.txt"
  prefix_guard_on_task_branch "git commit -F '$TEST_DIR/good.txt'"
  assert_allowed
  prefix_guard_on_task_branch "git commit -F '$TEST_DIR/bad.txt'"
  assert_denied
  prefix_guard_on_task_branch "git commit --file '$TEST_DIR/bad.txt'"
  assert_denied
  prefix_guard_on_task_branch "git commit --file='$TEST_DIR/bad.txt'"
  assert_denied
}

@test "commit-prefix-guard: checks a heredoc piped into -F -" {
  prefix_guard_on_task_branch "cat <<'MSG' | git commit -F -
task-99: fix the widget

It's done.
MSG"
  assert_allowed
  prefix_guard_on_task_branch "cat <<'MSG' | git commit -F -
fix the widget
MSG"
  assert_denied
}

@test "commit-prefix-guard: checks a heredoc on -F - itself" {
  prefix_guard_on_task_branch "git commit -F - <<'MSG'
fix the widget
MSG"
  assert_denied
}

@test "commit-prefix-guard: checks an -m built from a cat heredoc" {
  prefix_guard_on_task_branch "git commit -m \"\$(cat <<'EOF'
task-99: it's \"done\"

Body.
EOF
)\""
  assert_allowed
  prefix_guard_on_task_branch "git commit -m \"\$(cat <<'EOF'
it's not prefixed
EOF
)\""
  assert_denied
}

@test "commit-prefix-guard: sees a commit after env assignments, git -C and a separator" {
  prefix_guard_on_task_branch 'git add -u && PATH=/usr/bin:$PATH git -C . commit -am "no prefix" 2>&1 | tail -1'
  assert_denied
}

@test "commit-prefix-guard: allows a commit whose message cannot be extracted" {
  prefix_guard_on_task_branch 'git commit --amend --no-edit'
  assert_allowed
  prefix_guard_on_task_branch 'git commit -F /nonexistent/msg.txt'
  assert_allowed
}

@test "commit-prefix-guard: attached -S and -u values do not hide the message" {
  prefix_guard_on_task_branch "git commit -unormal -Spaul@mail.com -m 'task-99: signed'"
  assert_allowed
  prefix_guard_on_task_branch "git commit -Smykey -m 'not prefixed'"
  assert_denied
}

@test "commit-prefix-guard: sees a commit behind env, command and time wrappers" {
  prefix_guard_on_task_branch "env git commit -m 'x'"
  assert_denied
  prefix_guard_on_task_branch "time command git commit -m 'x'"
  assert_denied
}

@test "commit-prefix-guard: allows a subject that only expansion can reveal" {
  prefix_guard_on_task_branch "git commit -m \"\$(printf 'task-99: x')\""
  assert_allowed
  prefix_guard_on_task_branch 'git commit -m "$MSG"'
  assert_allowed
}

@test "commit-prefix-guard: still checks a message whose body holds backticks" {
  prefix_guard_on_task_branch "git commit -m \"\$(cat <<'EOF'
not prefixed

Run \`make\`.
EOF
)\""
  assert_denied
}
