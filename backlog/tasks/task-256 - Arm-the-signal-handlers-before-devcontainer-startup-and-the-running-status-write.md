---
id: TASK-256
title: >-
  Arm the signal handlers before devcontainer startup and the running status
  write
status: Done
assignee: []
created_date: '2026-10-01 05:46'
updated_date: '2026-10-01 06:07'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

`plugins/ralph/skills/ralph-run/scripts/ralph/loop.py` installs the SIGINT/SIGTERM handlers far too late in `run()`. Current order:

- line ~125 `start_devcontainer(project_root, rebuild=args.rebuild)` — **minutes** on `--rebuild`
- line ~156 `status.write_atomic(status_path)` — publishes `state="running"`
- line ~162 `push_enabled()` / `current_rev()` — forks a **git subprocess**
- line ~169 `build_tool(...)`
- line ~170 `installer = _SignalInstaller()` / `installer.install()`

Any SIGINT/SIGTERM before `install()` hits Python's default disposition and kills the process outright: wait status "killed by signal 15", exit `-15`, no handler, no graceful drain.

**Product impact (the reason this is not test hygiene).** `/ralph-stop` sends SIGTERM, and `ralph-stop`'s own description promises "SIGTERM for graceful shutdown" and that it "stops it from spawning the *next* iteration". During the whole startup phase that promise is not kept. Because the kill lands before the first status write, the run leaves **no status file at all**: `/ralph-status` then reports the *previous* run's state, and ralph-run's heartbeat wait reports the launch as dead. Startup — especially a multi-minute `--rebuild` — is a likely moment for an operator to change their mind and stop.

**Test impact.** `plugins/ralph/skills/ralph-run/tests/test_loop_signal_interrupt.py::test_orchestrator_exits_promptly_on_sigterm` waits for `state == "running"` then sends SIGTERM, so it races the gap between the status write and `install()`. It has been reporting this defect as an intermittent failure (`AssertionError: exit code -15, expected 130`) and was repeatedly dismissed as flaky. Measured on 2026-10-01: `git rev-parse` takes 7-80ms (median 16ms idle) and the test polls every 100ms, so it loses the race roughly one run in five, more under suite load.

## Verified mechanism (2026-10-01, not inferred)

Inserting a 2-second sleep in the gap reproduces the failure verbatim:

```python
    status.write_atomic(status_path)
    import time as _t; _t.sleep(2)   # probe
```

→ `AssertionError: exit code -15, expected 130`, deterministically.

Moving the installer above the status write, with the same 2s probe still in place, makes all 8 tests in that file pass. That isolates the window to those ~14 lines.

## Direction

Arm the handlers at the top of `run()`, before `start_devcontainer()`. Arming early is already safe: `_SignalInstaller._handler` returns early when `_active_pgid is None`, so with no tool subprocess registered it only sets the pending flag.

Two details must be handled, or the fix trades one bug for another:

1. **`raise_if_pending()` is first called at line ~229, inside the per-iteration loop.** A SIGTERM during container startup would set the flag and then still run `start_devcontainer` to completion and enter the loop before raising. Add a check immediately after `start_devcontainer` returns, so a stop during a rebuild exits promptly instead of finishing a container nobody wants.
2. **`installer.restore()` lives in the `finally` of the block wrapping `_run_loop`.** Moving `install()` earlier means moving that try/finally boundary with it, or `restore()` leaks on the early paths.

The invariant to pin: **once the status file says `running`, the handlers are armed.** That is the contract both `ralph-status-watch` and `ralph-stop` rely on.

## Decide explicitly, do not change silently

SIGTERM currently maps to exit `130` (`state.exit_code = 130` at line ~188). 130 is 128+SIGINT; SIGTERM would conventionally be 143. Keep 130 or split per signal — but make it a deliberate call and record the reason, since `ralph.sh` parity and the existing assertions may depend on it.

## Out of scope

- Reworking the flag-and-poll design, or where `raise_if_pending` is called inside the loop.
- `ralph-stop`'s in-container behaviour (it deliberately does not reach the containerized agent).
- The two APFS-only `pre-commit` bats failures (#34/#35), which are unrelated.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Signal handlers are installed before start_devcontainer() is called, so a SIGTERM during container startup is handled rather than killing the process with signal 15
- [x] #2 A SIGTERM arriving during startup causes a prompt exit without running the iteration loop, verified by a test that signals before the loop begins
- [x] #3 installer.restore() still runs on every exit path after the install() move, including the early devcontainer-failure return
- [x] #4 A test asserts the invariant that the handlers are armed by the time the status file reports state=running
- [x] #5 test_orchestrator_exits_promptly_on_sigterm passes with a deliberate multi-second delay inserted between the running status write and the start of the iteration loop, demonstrating the race window is closed
- [x] #6 The SIGTERM exit code is either kept at 130 or changed deliberately, with the choice and its rationale recorded in the task notes
- [x] #7 uv run ruff check . and uv run pytest both pass, and the full suite runs three consecutive times with no intermittent failure in test_loop_signal_interrupt.py
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: wrap run() so _SignalInstaller is installed before start_devcontainer and restored in an outer finally; move the body into _run_armed with raise_if_pending() right after bring-up (before the running write) inside the existing except/finally so _finalize records interrupted/130; extract _initial_status. Tests: startup-delay variant of the E2E SIGTERM test (stalls build_tool after the running write), in-process SIGTERM-during-bring-up, devcontainer-failure restore, armed-at-every-running-write invariant.

Commit: `cf9fc9a` - task-256: arm signal handlers before devcontainer startup and the running status write

Exit-code decision (AC #6): SIGTERM keeps exit 130, same as SIGINT. Reason: ralph-refine documents 130 for SIGINT/SIGTERM and refine/loop.py returns it, the status-file exit_code and the E2E assertions consume 130 as the single 'interrupted' code, and ralph.sh has no separate SIGTERM code to keep parity with. Splitting to 143 would fork the interrupted contract between the two loops for no consumer benefit.
AC #5 evidence: test_orchestrator_exits_promptly_on_sigterm[startup-delay] stalls build_tool 3s after the running write; against master loop.py it fails (exit -15), with the fix it passes. All four new tests fail on master loop.py. Full suite 682 passed x3, ruff clean.

Review: task-reviewer APPROVED. Non-blocking follow-up noted: if a stop arrives during bring-up AND start_devcontainer then fails (e.g. Ctrl-C kills the devcontainer CLI too), run() returns that rc with no status file rather than 130.

Commit: `d697416` - task-256: bump plugin version to 0.8.4 (patch)
<!-- SECTION:NOTES:END -->
