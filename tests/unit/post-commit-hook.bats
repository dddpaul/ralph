#!/usr/bin/env bats
# Unit tests for plugins/ralph/skills/ralph-init/templates/git-hooks/post-commit
#
# The hook appends a "Commit: `<hash>` - <subject>" note to the task named by
# the task-* branch. It skips commits that touch only task files (status / AC /
# notes bookkeeping); commits to backlog/docs/ etc. carry task work and must
# still be recorded, otherwise /ralph-review finds no Commit lines.

load '../helpers/common'
HOOK="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/git-hooks/post-commit"

setup() {
  TEST_DIR="$(make_temp_dir)"
  cd "$TEST_DIR"
  git init -q
  git config user.email test@example.com
  git config user.name Test
  git config commit.gpgsign false
  cp "$HOOK" .git/hooks/post-commit
  chmod +x .git/hooks/post-commit

  # Stub backlog CLI: write the --append-notes value into the task file.
  mkdir -p bin
  cat > bin/backlog <<'EOF'
#!/bin/bash
note=""
while [ $# -gt 0 ]; do
    case "$1" in
        --append-notes) note="$2"; shift ;;
    esac
    shift
done
f=$(ls "$(git rev-parse --show-toplevel)"/backlog/tasks/task-1*.md | head -1)
printf '%s\n' "$note" >> "$f"
EOF
  chmod +x bin/backlog
  PATH="$TEST_DIR/bin:$PATH"

  mkdir -p backlog/tasks backlog/docs
  TASK_FILE="backlog/tasks/task-1 - Task.md"
  echo "# task-1" > "$TASK_FILE"
  echo "bin/" > .gitignore
  git add -A
  git commit -q -m "init"
  git checkout -q -b task-1
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

commit_lines() {
  grep -c '^Commit: `' "$TASK_FILE" || true
}

@test "post-commit: commit touching only backlog/tasks/ records no Commit line" {
  echo "status" >> "$TASK_FILE"
  git add -A
  git commit -q -m "task-1: tick AC"
  [ "$(commit_lines)" -eq 0 ]
}

@test "post-commit: commit adding a non-ASCII task file records no Commit line" {
  # git quotes non-ASCII paths by default ("backlog/tasks/\320..."); the hook
  # must still see them as backlog/tasks/ paths.
  echo "new" > "backlog/tasks/task-2 - Задача.md"
  git add -A
  git commit -q -m "task-1: add task-2"
  [ "$(commit_lines)" -eq 0 ]
}

@test "post-commit: commit touching only backlog/archive/ records no Commit line" {
  mkdir -p backlog/archive/tasks
  echo "old" > "backlog/archive/tasks/task-9 - Old.md"
  git add -A
  git commit -q -m "task-1: archive task-9"
  [ "$(commit_lines)" -eq 0 ]
}

@test "post-commit: commit touching backlog/docs/ and backlog/tasks/ records a Commit line" {
  echo "body" > "backlog/docs/doc-1 - Doc.md"
  echo "status" >> "$TASK_FILE"
  git add -A
  git commit -q -m "task-1: write doc-1"
  [ "$(commit_lines)" -eq 1 ]
  grep -q "^Commit: \`$(git rev-parse --short HEAD)\` - task-1: write doc-1$" "$TASK_FILE"
}

@test "post-commit: commit touching only backlog/docs/ records a Commit line" {
  echo "body" > "backlog/docs/doc-1 - Doc.md"
  git add -A
  git commit -q -m "task-1: write doc-1"
  [ "$(commit_lines)" -eq 1 ]
}

@test "post-commit: commit touching a file outside backlog/ records a Commit line" {
  echo "code" > app.sh
  git add -A
  git commit -q -m "task-1: add app"
  [ "$(commit_lines)" -eq 1 ]
  grep -q "^Commit: \`$(git rev-parse --short HEAD)\` - task-1: add app$" "$TASK_FILE"
}
