---
id: TASK-22
title: Consolidate failure tracking between timeout and error paths
status: To Do
assignee: []
created_date: '2026-04-19 10:20'
updated_date: '2026-04-19 15:17'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph.sh has two separate failure-counting code paths:
1. Timeout path (lines 366-373): inlines FAILED_ITERATIONS++ and calls _append_status_error directly
2. Regular error path (lines 377-391): goes through handle_error() which has its own bookkeeping

This duplication risks divergence — bug fixes to one path may not be applied to the other. The status file's failure count and the summary's FAILED_ITERATIONS count can drift.

Fix: extract a single _record_iteration_failure() function that takes a reason string, increments FAILED_ITERATIONS, calls _append_status_error, and sets ITER_FAILED=true. Call it from both the timeout path and inside handle_error().
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Single _record_iteration_failure() function exists and is called from both timeout and error paths
- [ ] #2 FAILED_ITERATIONS count matches the number of error entries in the status file
- [ ] #3 Existing tests in run-summary-integration.bats and timeout-handling.bats still pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Brainstorm Design (2026-04-19)

Full refactor with helper function. Also fixes a pre-existing bookkeeping inconsistency.

## Pre-existing bug being fixed as a bonus

Currently handle_error() at ralph.sh:259 calls _append_status_error() every time it's invoked, including on retry attempts that ultimately succeed. But FAILED_ITERATIONS is only incremented in terminal branches. Result: STATUS_ERRORS can have more entries than FAILED_ITERATIONS count (e.g. 3 retry attempts that eventually succeed → 3 status errors logged, 0 failed iterations counted).

The refactor naturally fixes this by moving _append_status_error() into the terminal branches only.

## New helper function

Add near existing helpers (after _append_status_error, around line 178):

```bash
_record_iteration_failure() {
  local reason="$1"
  FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
  _append_status_error "$reason"
  ITER_FAILED=true
}
```

## Changes to timeout path (ralph.sh:366-373)

Replace:
```bash
if [[ $EXIT_CODE -eq 124 ]]; then
  echo ""
  echo "WARNING: Iteration $i timed out after ${TIMEOUT}m ($(format_duration $(($(date +%s) - ITER_START)))). Continuing to next iteration..."
  FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
  ITER_FAILED=true
  _append_status_error "Iteration $i timed out after ${TIMEOUT}m"
  sleep 2
  break
fi
```

With:
```bash
if [[ $EXIT_CODE -eq 124 ]]; then
  echo ""
  echo "WARNING: Iteration $i timed out after ${TIMEOUT}m ($(format_duration $(($(date +%s) - ITER_START)))). Continuing to next iteration..."
  _record_iteration_failure "Iteration $i timed out after ${TIMEOUT}m"
  sleep 2
  break
fi
```

## Changes to handle_error (ralph.sh:253-289)

**Remove** the unconditional `_append_status_error` call at line 259.

**Move** the call into each terminal branch via _record_iteration_failure:

```bash
handle_error() {
  local exit_code="$1"
  local iteration="$2"
  local retry_attempt="$3"

  log_error "Iteration $iteration failed with exit code $exit_code (tool: $TOOL, retry: $retry_attempt)"

  case "$ON_ERROR" in
    stop)
      echo "ERROR: AI tool failed with exit code $exit_code. Stopping."
      EXIT_REASON="error"
      _record_iteration_failure "Iteration $iteration failed with exit code $exit_code"
      LAST_ITER_DURATION=$(( $(date +%s) - ITER_START ))
      ITER_DURATIONS+=("$LAST_ITER_DURATION")
      cleanup_and_exit "$exit_code"
      ;;
    continue)
      echo "WARNING: AI tool failed with exit code $exit_code. Continuing to next iteration..."
      _record_iteration_failure "Iteration $iteration failed with exit code $exit_code"
      return 1
      ;;
    retry)
      if [[ $retry_attempt -lt $RETRY_COUNT ]]; then
        echo "WARNING: AI tool failed with exit code $exit_code. Retrying (attempt $((retry_attempt + 1)) of $RETRY_COUNT)..."
        return 2
      else
        echo "ERROR: AI tool failed after $RETRY_COUNT retries. Stopping."
        EXIT_REASON="error"
        _record_iteration_failure "Iteration $iteration failed with exit code $exit_code"
        LAST_ITER_DURATION=$(( $(date +%s) - ITER_START ))
        ITER_DURATIONS+=("$LAST_ITER_DURATION")
        cleanup_and_exit "$exit_code"
      fi
      ;;
  esac
}
```

## Changes to caller (ralph.sh:381-385)

Remove the redundant `ITER_FAILED=true` at line 383 — handle_error now sets it via the helper:

```bash
if [[ $handler_result -eq 1 ]]; then
  # continue strategy - ITER_FAILED already set by handle_error
  break
fi
```

## Retry behavior — explicit note

After refactor:
- Retry attempt that succeeds → 0 calls to _record_iteration_failure, 0 status errors, 0 failed iterations (correct)
- Retry attempt that fails and exhausts retries → 1 call to _record_iteration_failure (in the retry-exhausted branch), 1 status error, 1 failed iteration (correct)
- Before the refactor, retry-that-succeeds appended N status errors but counted 0 failures — this inconsistency goes away

## New test to lock in the bug fix

Add to tests/integration/run-summary-integration.bats:

```bash
@test "status errors count matches failed iterations after retries that succeed" {
  # Mock tool that fails twice then succeeds
  # Run with --on-error=retry --retry-count=2
  # Assert: STATUS_ERRORS count == FAILED_ITERATIONS == 0
}
```

## Acceptance criteria update

Existing ACs still valid. Add:
- AC4: A retry-that-succeeds scenario leaves STATUS_ERRORS count equal to FAILED_ITERATIONS count (both 0)

## Additional scope: max-iterations exit semantics (2026-04-19)

Related brainstorm while running Ralph with max_iterations=1 showed the current 'max iterations reached' behavior conflates successful productive runs with failures.

**Problem:** ralph.sh lines 447-448 always exit 1 when max_iterations is reached, producing state='failed' even when the agent completed tasks successfully. For single-iteration runs this is especially misleading.

## Behavior matrix (new)

| TASKS_COMPLETED | FAILED_ITERATIONS | Exit code | State |
|---|---|---|---|
| 0 | 0 | 1 | failed (no progress) |
| 0 | >0 | 1 | failed (all failed) |
| >0 | 0 | **0** | **completed** (productive run, iterations exhausted) |
| >0 | >0 | 1 | failed (strict — any failure taints the run) |

Success criterion: TASKS_COMPLETED > 0 AND FAILED_ITERATIONS == 0.

## Change to ralph.sh (lines 447-448)

Replace:
```bash
EXIT_REASON="max iterations reached"
cleanup_and_exit 1
```

With:
```bash
if [[ "$TASKS_COMPLETED" -gt 0 && "$FAILED_ITERATIONS" -eq 0 ]]; then
  EXIT_REASON="max iterations reached ($TASKS_COMPLETED task(s) completed)"
  cleanup_and_exit 0
else
  EXIT_REASON="max iterations reached"
  cleanup_and_exit 1
fi
```

`cleanup_and_exit` itself is unchanged — state still derives from exit code via its existing logic (line 190).

## Test updates

- **Update existing:** tests/integration/run-summary-integration.bats test 'summary on max iterations reached' currently asserts exit 1; split into two tests or update to match new matrix
- **New cases to add:**
  1. max_iterations=1, agent succeeds (TASKS_COMPLETED=1, no failures) → exit 0, state='completed'
  2. max_iterations=1, agent times out → exit 1, state='failed'
  3. max_iterations=3, all succeed → exit 0, state='completed'
  4. max_iterations=3, mixed 2 success + 1 failure (strict criterion) → exit 1, state='failed'

## Additional acceptance criteria

- AC5: End-of-loop exit uses TASKS_COMPLETED + FAILED_ITERATIONS to decide exit code (0 for productive, 1 for failures or no progress)
- AC6: max_iterations=1 with successful agent produces state='completed' and exit code 0
- AC7: Mixed-outcome runs (any FAILED_ITERATIONS > 0) produce state='failed' regardless of TASKS_COMPLETED
<!-- SECTION:NOTES:END -->
