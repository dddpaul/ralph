---
id: TASK-21
title: Fix tee output buffering loss on ralph.sh crash
status: To Do
assignee: []
created_date: '2026-04-19 10:20'
updated_date: '2026-04-19 14:08'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph.sh:303 uses 'exec > >(tee -a "$RUN_LOG") 2>&1' to log all output. Bash process substitution can buffer output; if ralph crashes, the last lines of output may not be flushed to RUN_LOG. This makes post-mortem debugging harder because the actual failure context is missing from the log.

Fix: use 'stdbuf -oL -eL tee' (line-buffered) on Linux, or write directly to a file descriptor with explicit flushing. Note that stdbuf may not be available on macOS without coreutils; consider an alternative like writing to file via 'exec >> $RUN_LOG' and using 'tail -f' for live viewing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh logs are flushed line-by-line, not buffered
- [ ] #2 When ralph.sh crashes, the last output lines appear in RUN_LOG
- [ ] #3 Solution works on both macOS and Linux containers
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Brainstorm Design (2026-04-19)

Original task assumed tee buffering is an actual bug. On reflection, this may be theoretical — bash echo/printf are line-buffered (use write() syscalls), GNU tee to a file is line-buffered, and on ralph.sh crash the kernel closes the pipe and tee drains remaining data before exit. No concrete bug report exists.

**Reframing as investigation task.** Prove or disprove the bug before writing a fix.

## Phase 1: Reproducer

Add a standalone reproducer test at tests/integration/tee-buffering.bats:

```bash
#\!/usr/bin/env bats

@test "tee-via-process-substitution preserves tail output on SIGKILL" {
  OUTFILE="$BATS_TEST_TMPDIR/tee-test.log"
  (
    exec > >(tee -a "$OUTFILE") 2>&1
    for i in $(seq 1 100000); do
      echo "line $i"
    done
    echo "FINAL_LINE"
    kill -9 $$
  ) 2>/dev/null
  sleep 0.5
  last=$(tail -1 "$OUTFILE")
  [[ "$last" == "FINAL_LINE" ]]
}
```

Run on both macOS (host) and Ubuntu (devcontainer) to check platform-specific behavior (BSD tee vs GNU tee).

## Phase 2: Decision tree based on reproducer results

**Outcome A: All output present on both platforms**
→ Bug does not exist. Close TASK-21. Document evidence (sample reproducer runs) in task notes. Leave ralph.sh:303 unchanged.

**Outcome B: Tail missing on one platform only**
→ Scope fix to that platform. Most likely macOS BSD tee needs different handling.

**Outcome C: Tail missing on both platforms**
→ Apply fix. Preferred candidates in order:
  1. `stdbuf -oL tee -a "$RUN_LOG"` — requires GNU coreutils (not default on macOS, available on Linux containers)
  2. Direct append via `exec >> "$RUN_LOG" 2>&1` — loses live terminal output (UX regression)
  3. Dual-write helper: `_log() { echo "$*" | tee -a "$RUN_LOG"; }` — invasive refactor

## Scope changes

Original ACs replaced by investigation ACs:

- AC1: Reproducer test exists in tests/integration/tee-buffering.bats
- AC2: Reproducer has been run on both macOS host and Ubuntu devcontainer; results documented in this task's notes
- AC3: Decision made — if bug does not reproduce, task closed without ralph.sh changes; if bug reproduces, fix applied and reproducer passes
<!-- SECTION:NOTES:END -->
