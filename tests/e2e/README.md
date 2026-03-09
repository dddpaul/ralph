# E2E Tests for Ralph

This directory contains end-to-end tests for Ralph's autonomous agent loop.

## Automated E2E Tests

The automated E2E tests (`.bats` files) use **mocked opencode responses** to test Ralph's orchestration without requiring a real API key. These tests can run in CI/CD environments.

### Prerequisites for Automated Tests

1. **bats-core installed**: `npm install` (installs bats-core and dependencies)
2. **Backlog.md CLI mocked**: Tests create mock `backlog` commands
3. **Git repository**: Tests create temporary git repos

### Running Automated Tests

```bash
# Run all E2E tests
npm run test:e2e

# Or directly with bats
npx bats tests/e2e/
```

See `tests/helpers/` for mock implementations.

## Manual Test: Real opencode Integration

This test verifies that Ralph works correctly with the real opencode AI coding tool.

### Prerequisites for Manual Test

1. **opencode CLI installed**: `npm install -g @opencode/cli`
2. **API key configured**: Set your API key in the appropriate environment variable or opencode configuration
3. **Backlog.md CLI installed**: Required for task management
4. **Git repository**: Tests assume you're in a git repository

## Manual Test: Real opencode Integration

This test verifies that Ralph works correctly with the real opencode AI coding tool.

### Test Procedure

1. **Create test tasks**

   Create 3 simple test tasks that echo messages:

   ```bash
   # Task 1: Simple echo
   backlog task create "Echo test 1" -d "Add a test file that echoes hello" --ac "File tests/tmp/hello.txt exists containing 'hello'"

   # Task 2: Another echo
   backlog task create "Echo test 2" -d "Add a test file that echoes world" --ac "File tests/tmp/world.txt exists containing 'world'"

   # Task 3: Combined echo
   backlog task create "Echo test 3" -d "Add a test file combining both" --ac "File tests/tmp/hello-world.txt exists containing 'hello world'"
   ```

2. **Run Ralph with opencode**

   Execute Ralph with a limited iteration count:

   ```bash
   ./ralph.sh --tool opencode 5
   ```

3. **Verify task transitions**

   After Ralph completes, check that all tasks transitioned to "Done":

   ```bash
   backlog task list --plain
   ```

   Expected output:
   - All 3 test tasks should show status "Done"
   - No tasks should remain in "To Do" or "In Progress"

4. **Verify git commits**

   Check that each task has an associated commit:

   ```bash
   git log --oneline -10
   ```

   Expected:
   - Commits with messages like `task-<id>: <description>`
   - Each test task should have at least one commit

5. **Clean up test tasks**

   Remove the test tasks and files:

   ```bash
   # Remove task files (if needed)
   rm -rf tests/tmp

   # Archive or delete test tasks from backlog (optional)
   ```

### Expected Results

- ✅ All 3 test tasks transition from "To Do" → "In Progress" → "Done"
- ✅ Git commits created for each task
- ✅ Task branches created, merged to main, and deleted
- ✅ Task notes contain commit hashes
- ✅ Created files match acceptance criteria

### Troubleshooting

**Issue: opencode CLI not found**

Solution: Install opencode globally:
```bash
npm install -g @opencode/cli
```

**Issue: API key errors**

Solution: Configure your API key:
```bash
# Set environment variable or configure opencode
export OPENAI_API_KEY="your-key-here"
# OR follow opencode documentation for your provider
```

**Issue: Tasks stuck in "In Progress"**

Solution: Check the task notes for error messages:
```bash
backlog task <id> --plain
```
