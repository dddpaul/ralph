---
id: TASK-153
title: 'Implement claude-code subprocess with tee, timeout, and process-group cleanup'
status: To Do
assignee: []
created_date: '2026-06-21 13:08'
labels:
  - 'feature:ralph-python-refactor'
dependencies:
  - TASK-151
  - TASK-152
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-004 from design/ralph-python-refactor-prd.md.

Implement `ralph/tools/claude.py` to spawn the claude-code child with the same I/O semantics as bash (`claude --print 2>&1 | tee <outfile>`), enforce per-iteration timeout (exit 124 = timeout, NOT `--on-error` failure), and clean up the entire child process tree on signal.

Spec sources:
- `skills/ralph-run/scripts/ralph.sh` lines 560–650 (claude invocation, tee, timeout handling)
- `skills/ralph-run/scripts/ralph.sh` lines 530–560 (SIGTERM/SIGINT trap)
- `design/ralph-python-refactor-prd.md` §7 historical-context appendix entries titled "Subprocess management / process cleanup" and "I/O & streaming contract"
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `ralph/tools/claude.py` implements `Tool.run()`: spawns `claude --print` with stdin=prompt, stdout=PIPE, stderr=STDOUT
- [ ] #2 Subprocess launched with `start_new_session=True` (or `preexec_fn=os.setpgrp`) so child gets its own process group
- [ ] #3 Stdout consumed line-by-line via a background-thread queue; each line is written to BOTH a temp tee file AND a real-time sentinel scanner
- [ ] #4 Per-iteration timeout enforced via `Popen.wait(timeout=...)`; on timeout: SIGTERM to process group, wait 5s, then SIGKILL; orchestrator continues (NOT treated as --on-error failure)
- [ ] #5 SIGTERM handler kills child's process group, flushes RUN_LOG, final status JSON write sets `state=failed` (no separate `interrupted` state)
- [ ] #6 Devcontainer prefix support: argv is a LIST `["devcontainer", "exec", "--workspace-folder", <path>, "claude", "--print"]` — never a joined string
- [ ] #7 Unit test: spawn a sleeper child via `tools/claude.py`, send SIGTERM, assert child gone within 5s (no zombie process)
- [ ] #8 Unit test: spawn a child that exits 124; assert orchestrator treats it as timeout (continues to next iteration, no failure recorded)
- [ ] #9 `uv run pyright skills/ralph-run/scripts` passes
- [ ] #10 `uv run ruff check skills/ralph-run/scripts` passes
- [ ] #11 `uv run pytest skills/ralph-run/tests/` passes
<!-- AC:END -->
