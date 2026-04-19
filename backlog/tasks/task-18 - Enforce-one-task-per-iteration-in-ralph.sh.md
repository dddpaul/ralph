---
id: TASK-18
title: Enforce one task per iteration in ralph.sh
status: To Do
assignee: []
created_date: '2026-04-19 10:19'
updated_date: '2026-04-19 10:31'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph.sh tells the agent in the prompt to do one task per iteration but never verifies it. A misbehaving agent could complete multiple tasks silently in one iteration, breaking the isolation model where each task gets a fresh Claude instance.

Fix: after each iteration, parse OUTFILE (the captured agent output) and count the number of '## Task Summary' blocks. If count is 0 or >1, log a warning and increment FAILED_ITERATIONS. Optionally, fail the iteration based on a new --strict-one-task flag.

Location: ralph.sh:360 (where OUTFILE is written). Add the check after line 395 (end of retry loop) before line 397 (ITER_ELAPSED calculation).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After each iteration, ralph.sh counts '## Task Summary' blocks in OUTFILE
- [ ] #2 If count \!= 1, a warning is logged to RUN_LOG and to stderr
- [ ] #3 Test added in tests/integration/ to verify warning is emitted when agent outputs 0 or 2 Task Summary blocks
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Brainstorm Design (2026-04-19)

**Behavior chosen:** Observability only — log warning when block count \!= 1. No FAILED_ITERATIONS change, no exit code change, no abort.

**False-positive handling:** Skip the warning when COMPLETE signal is present (legitimate 0-block case). Still warn on timeout/error iterations — those already log separately, so the warning adds context.

**Location:** ralph.sh, between line 395 (end of retry loop) and line 419 (ITER_FAILED branch).

**Implementation:**
```bash
# After retry loop, before ITER_FAILED check
if \! grep -q '<promise>COMPLETE</promise>' "$OUTFILE"; then
  SUMMARY_COUNT=$(grep -c '^## Task Summary$' "$OUTFILE" || true)
  if [[ "$SUMMARY_COUNT" -ne 1 ]]; then
    echo "WARNING: Iteration $i produced $SUMMARY_COUNT '## Task Summary' blocks (expected 1). This may indicate the agent processed multiple tasks or none." >&2
  fi
fi
```

**Regex anchoring rationale:** `^## Task Summary$` (anchored) instead of `## Task Summary` to avoid matching when the agent quotes CLAUDE.md text (e.g. agent saying 'the `## Task Summary` block'). Only matches actual headings.

**COMPLETE check duplication:** The COMPLETE grep is also done at line 430. Duplication is acceptable — cheap grep, avoids reordering existing flow.

**Output destination:** stderr is sufficient; the existing `exec > >(tee -a "$RUN_LOG") 2>&1` at line 303 already routes stderr into RUN_LOG.

## Test Cases (tests/integration/)

Add to existing prompt-generation.bats or new file (e.g. one-task-enforcement.bats):

1. Mock agent outputs 0 Task Summary blocks (no COMPLETE) → warning emitted
2. Mock agent outputs 2 Task Summary blocks → warning emitted
3. Mock agent outputs exactly 1 Task Summary block → no warning
4. Mock agent outputs `<promise>COMPLETE</promise>` with 0 blocks → no warning (suppressed)
5. Mock agent times out (EXIT_CODE=124) with 0 blocks → warning still emitted

**Test mock:** assert via `grep -q 'WARNING.*Task Summary'` against captured stderr.
<!-- SECTION:NOTES:END -->
