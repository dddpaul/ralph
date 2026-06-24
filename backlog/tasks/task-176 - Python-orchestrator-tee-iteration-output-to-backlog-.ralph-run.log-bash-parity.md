---
id: TASK-176
title: >-
  Python orchestrator: tee iteration output to backlog/.ralph-run.log (bash
  parity)
status: Done
assignee: []
created_date: '2026-06-24 10:49'
updated_date: '2026-06-24 13:32'
labels:
  - bug
  - 'feature:ralph-python-refactor'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

`backlog/.ralph-run.log` is the canonical post-mortem log for a Ralph run: orchestrator decisions + every iteration's tool stdout/stderr tee'd into one project-rooted file. The bash orchestrator writes it continuously (`ralph.sh:461,692-694`); the Python orchestrator does NOT.

Symptom observed in a host downstream project (ethiopia, impl=python default): after a successful Python orchestrator run, `backlog/.ralph-run.log` does not exist. `wait_heartbeat.py:73` even tries to tail it on failure and emits literal `(run log not created)`. Without this file, downstream debugging of "what did iteration N actually do" is impossible — and the failure-path diagnostic loses its primary signal.

Root cause: Python orchestrator tees subprocess output to a tempfile per iteration (`tools/_subprocess.py:70-71` — `tempfile.mkstemp(prefix=tee_prefix, suffix='.out')`), but `loop.py` never (a) truncates a project-rooted `backlog/.ralph-run.log` at startup, nor (b) appends each iteration's tee target into it. The bash parity counterpart at `ralph.sh:692-694`:

```bash
: > "$RUN_LOG"
exec > >(tee -a "$RUN_LOG") 2>&1
```

is missing on the Python side. This is a regression blocking TASK-156 (bash cutover) — bash users `tail backlog/.ralph-run.log` works, Python users get nothing.

## Scope

In scope:
- Python orchestrator pre-loop setup: truncate `<project_root>/backlog/.ralph-run.log` exactly once at orchestrator start (parity with `ralph.sh:692` `: > "$RUN_LOG"`).
- Per-iteration subprocess tee: append each iteration's stdout/stderr to `backlog/.ralph-run.log` in addition to the existing per-iteration tempfile (preserve, do not replace).
- Preserve bash log semantics: header + iteration banners visible in the file as a run proceeds.
- Cover with an orchestrator test asserting a multi-iteration Python run produces a project-rooted `backlog/.ralph-run.log` whose size grows across iterations.

Out of scope:
- Removing the per-iteration tempfile mechanism in `_subprocess.py` — both targets must be written.
- Changes to heartbeat (`backlog/.ralph-heartbeat`), status (`backlog/.ralph-status.json`), or launch log (`backlog/.ralph-launch.log`).
- Log rotation / compression — bash has none and parity is the only goal here.

## Files

- `skills/ralph-run/scripts/ralph.sh` (exists, lines 461 + 692-694) — bash reference; do NOT modify, only mirror its semantics.
- `skills/ralph-run/scripts/ralph/loop.py` (exists, ~16KB, pre-loop setup around `run()`) — add truncate-on-start of `<project_root>/backlog/.ralph-run.log`; propagate path into tool invocation so `_subprocess.execute` can append.
- `skills/ralph-run/scripts/ralph/tools/_subprocess.py` (exists, lines 70-71 + 130-148) — extend `_stream_to_tee` (or the caller) to also append into the project-rooted run log, NOT replace the tempfile path.
- `skills/ralph-run/scripts/ralph/wait_heartbeat.py` (exists, line 73) — no change needed; will start displaying real content once the file exists.

## Source

Source: /Users/paul/Private/Alfa/Projects/duedil/ethiopia@98798c7078c1
Discovered while running TASK-15 via /ralph-run tasks=15 impl=python (default). Observed: run completed (state=completed, exit_code=0) but \`backlog/.ralph-run.log\` was absent from the project root; only `backlog/.ralph-heartbeat` and `backlog/.ralph-status.json` were written + cleaned up.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo (run `ls skills/ralph-run/scripts/ralph.sh skills/ralph-run/scripts/ralph/loop.py skills/ralph-run/scripts/ralph/tools/_subprocess.py skills/ralph-run/scripts/ralph/wait_heartbeat.py`).
2. Each AC is objectively pass/fail (file existence + grep + size comparison + test invocation — not "works correctly").
3. No dependencies in frontmatter (this is standalone, but conceptually unblocks TASK-156).
4. Out-of-scope items are not accidentally pulled in by ambiguous AC (do NOT touch heartbeat/status/launch-log code).

If anything is unclear or any check fails: STOP and ask the user.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 After Python orchestrator startup but before iteration 1 runs, <project_root>/backlog/.ralph-run.log is truncated to zero bytes (parity with ralph.sh:692 `: > \"\$RUN_LOG\"`)
- [x] #2 Each iteration tool subprocess stdout+stderr is appended to <project_root>/backlog/.ralph-run.log in addition to the existing per-iteration tempfile in tools/_subprocess.py
- [x] #3 After a 2-iteration Python orchestrator run, the file size after iteration 2 is strictly greater than after iteration 1 (the file grows, not overwritten per iteration)
- [x] #4 Per-iteration tempfile mechanism in tools/_subprocess.py is preserved — tee writes to BOTH the tempfile and the project-rooted run log; verified by inspecting tools/_subprocess.py for an unchanged tempfile.mkstemp call plus a new append target
- [x] #5 New test in the orchestrator suite asserts the above: launches a fake-tool 2-iteration run, asserts project-rooted backlog/.ralph-run.log exists, is non-empty, and grew between iterations
- [x] #6 After a successful single-iteration Python orchestrator run, <project_root>/backlog/.ralph-run.log exists and is non-empty (size > 0). Verifiable via pytest scripted-tool run OR live uv run invocation.
- [x] #7 wait_heartbeat.py:73 is unchanged; the literal string '(run log not created)' no longer appears in normal runs because the orchestrator creates the file at startup per AC #1 (derived property; no new test required).
- [x] #8 Python orchestrator honors RALPH_RUN_LOG env override; falls back to <project_root>/backlog/.ralph-run.log when unset (mirrors ralph.sh:461 \${RALPH_RUN_LOG:-...} default). Verifiable by test that sets RALPH_RUN_LOG=<tmp_path>/custom.log and asserts that path receives the appended output.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. loop.py: _run_log_file_path(project_root) honors RALPH_RUN_LOG env (parity with ralph.sh:461); run() truncates path before _run_loop (parity with ralph.sh:692 ': > $RUN_LOG'), plumbs path to build_tool().
2. tools/claude.py + tools/opencode.py: constructors accept run_log_path; forward to execute().
3. tools/_subprocess.py: execute() opens run_log_path append-binary alongside the tempfile; _spawn_and_stream / _stream_to_tee write each line to BOTH the tempfile AND the run log (tempfile preserved per AC #4); writes are best-effort, OSError suppressed.
4. tests/test_loop_run_log.py: 2-iter fake_claude run → assert backlog/.ralph-run.log exists, non-empty, grew between iterations (AC #5, #6); RALPH_RUN_LOG override test (AC #8).

Commit: `74b290c` - task-176: Python orchestrator tees iteration output to backlog/.ralph-run.log

Implementation:
- loop.py: _run_log_file_path() honors RALPH_RUN_LOG env (parity ralph.sh:461); _truncate_run_log() ': > $RUN_LOG' parity (ralph.sh:692); plumbs run_log_path through build_tool().
- tools/{claude,opencode}.py: constructors accept run_log_path; forward to execute().
- tools/_subprocess.py: execute() opens run_log_path 'ab' alongside the tempfile via ExitStack; _stream_to_tee writes each line to BOTH targets; tempfile.mkstemp call preserved per AC #4.
- tests/test_loop_run_log.py: 2-iter fake_claude run (task_done_no_summary mode) → banner-count==2 proves file grew (AC #3/#5/#6); RALPH_RUN_LOG override test (AC #8).

Verification:
- Full suite: 209/209 passed (uv run pytest)
- Lint: ruff clean on all 5 changed files
- task-reviewer: APPROVED (8/8 ACs verified, scope narrow, no parity-mirror collateral)
<!-- SECTION:NOTES:END -->
