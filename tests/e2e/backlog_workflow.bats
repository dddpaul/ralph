#!/usr/bin/env bats
# E2E tests for backlog workflow with mocked opencode

load '../helpers/common'

setup() {
  setup_test_dir
  TEST_REPO="$TEST_DIR/test-repo"
}

teardown() {
  cleanup_test_dir
}

create_test_repo() {
  mkdir -p "$TEST_REPO"
  cd "$TEST_REPO"
  git init
  git config user.email "test@test.com"
  git config user.name "Test User"
  
  # Create minimal backlog structure
  mkdir -p backlog/tasks backlog/docs
  echo "name: Test Project" > backlog/config.yml
  
  # Create test tasks
  cat > backlog/tasks/task-1-test-task-one.md <<'EOF'
---
id: TASK-1
title: Test task one
status: To Do
created_date: '2026-03-07'
---
# Test task one

Simple test task.
EOF

  cat > backlog/tasks/task-2-test-task-two.md <<'EOF'
---
id: TASK-2
title: Test task two
status: To Do
created_date: '2026-03-07'
---
# Test task two

Another test task.
EOF

  cat > backlog/tasks/task-3-test-task-three.md <<'EOF'
---
id: TASK-3
title: Test task three
status: To Do
created_date: '2026-03-07'
---
# Test task three

Third test task.
EOF
}

mock_opencode_completes_tasks() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'SCRIPT'
#!/bin/bash
# Mock opencode that "completes" a task

# Find the first To Do task
TASK_FILE=$(find backlog/tasks -name "*.md" -exec grep -l "status: To Do" {} \; | head -1)

if [[ -n "$TASK_FILE" ]]; then
  # Update status to Done
  sed -i 's/status: To Do/status: Done/' "$TASK_FILE"
  
  # Add some notes
  echo "" >> "$TASK_FILE"
  echo "## Notes" >> "$TASK_FILE"
  echo "Task completed by mock opencode" >> "$TASK_FILE"
fi

# Output completion signal
echo "## Task Summary"
echo "- Task: Mocked task completion"
echo "- What was implemented: Nothing (mock)"
echo "- Files changed: none"
echo "- Key decisions: none"
SCRIPT
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
}

mock_opencode_completes_all() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/opencode" <<'SCRIPT'
#!/bin/bash
# Mock opencode that marks all tasks as Done and signals completion

for TASK_FILE in backlog/tasks/*.md; do
  if [[ -f "$TASK_FILE" ]]; then
    sed -i 's/status: To Do/status: Done/' "$TASK_FILE"
    sed -i 's/status: In Progress/status: Done/' "$TASK_FILE"
  fi
done

echo "<promise>COMPLETE</promise>"
SCRIPT
  chmod +x "$TEST_DIR/bin/opencode"
  export PATH="$TEST_DIR/bin:$PATH"
}

mock_backlog_list() {
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/backlog" <<'SCRIPT'
#!/bin/bash
if [[ "$1" == "task" && "$2" == "list" ]]; then
  # Count To Do tasks
  TODO_COUNT=$(find backlog/tasks -name "*.md" -exec grep -l "status: To Do" {} \; 2>/dev/null | wc -l)
  
  if [[ "$TODO_COUNT" -eq 0 ]]; then
    echo "No tasks found"
  else
    find backlog/tasks -name "*.md" -exec grep -l "status: To Do" {} \; | while read f; do
      ID=$(grep "^id:" "$f" | cut -d' ' -f2)
      TITLE=$(grep "^title:" "$f" | cut -d' ' -f2-)
      echo "$ID - $TITLE"
    done
  fi
else
  echo "backlog mocked"
fi
SCRIPT
  chmod +x "$TEST_DIR/bin/backlog"
  export PATH="$TEST_DIR/bin:$PATH"
}

@test "E2E: Initialize git repo and backlog in temp directory" {
  create_test_repo
  
  [[ -d "$TEST_REPO/.git" ]]
  [[ -d "$TEST_REPO/backlog/tasks" ]]
  [[ -f "$TEST_REPO/backlog/config.yml" ]]
}

@test "E2E: Create 3 simple tasks in To Do status" {
  create_test_repo
  
  TODO_COUNT=$(find backlog/tasks -name "*.md" -exec grep -l "status: To Do" {} \; | wc -l)
  [[ "$TODO_COUNT" -eq 3 ]]
}

@test "E2E: Run ralph.sh with mock opencode that completes tasks" {
  create_test_repo
  mock_backlog_list
  mock_opencode_completes_all
  
  cd "$TEST_REPO"
  
  # Run ralph with mock
  RALPH_SCRIPT="$PROJECT_ROOT/ralph.sh"
  run timeout 30 bash "$RALPH_SCRIPT" --tool opencode --timeout 1 5
  
  [[ "$output" == *"Ralph completed all tasks!"* ]] || [[ "$output" == *"All tasks complete"* ]]
}

@test "E2E: Verify tasks marked as Done after run" {
  create_test_repo
  mock_backlog_list
  mock_opencode_completes_all
  
  cd "$TEST_REPO"
  
  RALPH_SCRIPT="$PROJECT_ROOT/ralph.sh"
  run timeout 30 bash "$RALPH_SCRIPT" --tool opencode --timeout 1 5
  
  # Check all tasks are Done
  TODO_COUNT=$(find backlog/tasks -name "*.md" -exec grep -l "status: To Do" {} \; 2>/dev/null | wc -l || echo "0")
  [[ "$TODO_COUNT" -eq 0 ]]
}

@test "E2E: Cleanup temp files and directories after test" {
  create_test_repo
  
  [[ -d "$TEST_REPO" ]]
  
  # Teardown will clean up TEST_DIR which includes TEST_REPO
  cleanup_test_dir
  
  [[ ! -d "$TEST_REPO" ]]
}

@test "E2E: Full workflow with mock opencode" {
  create_test_repo
  mock_backlog_list
  mock_opencode_completes_all
  
  cd "$TEST_REPO"
  
  # Verify initial state
  TODO_COUNT=$(find backlog/tasks -name "*.md" -exec grep -l "status: To Do" {} \; | wc -l)
  [[ "$TODO_COUNT" -eq 3 ]]
  
  # Run ralph
  RALPH_SCRIPT="$PROJECT_ROOT/ralph.sh"
  run timeout 30 bash "$RALPH_SCRIPT" --tool opencode --timeout 1 5
  
  # Verify completion
  [[ "$status" -eq 0 ]]
  [[ "$output" == *"Ralph"* ]]
}
