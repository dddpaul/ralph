---
id: TASK-200
title: Audit Python orchestrator behavior deltas surfaced by TASK-199 bats retirement
status: Done
assignee: []
created_date: '2026-07-04 09:40'
updated_date: '2026-07-04 12:31'
labels:
  - tech-debt
  - python-orchestrator
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-199 retired bats tests that pinned bash-orchestrator behaviors the Python port does NOT replicate. Each is either an intentional simplification or a real gap — a human should triage. Deltas found: (1) --on-error retry / --retry-count: args.py accepts them (choices include 'retry') but loop.py treats 'retry' identically to 'continue' — a failed iteration is never re-run. (2) --log-file: parsed into args.log_file but never consumed anywhere in the loop/tools (grep: only args.py references it) — the flag is a silent no-op. (3) Task-summary block-count warning: signals.py computes task_summary_count and test_signals.py covers it, but loop.py never emits the bash 'WARNING: Iteration N produced X ## Task Summary blocks (expected 1)' message. (4) current_task null-clearing: bash re-derived current_task from the In Progress list on each status write (nulling it once the task moved to Done); Python sets current_task to the last-picked task and leaves it sticky. Reference: previously covered by tests/integration/{run-summary-integration,status-file-integration,one-task-enforcement}.bats before TASK-199.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of the 4 behavior deltas (--on-error retry, --log-file, task-summary-count warning, current_task null-clearing) is classified in the task notes as intentional-drop (behavior/flag removed) or real-gap (implemented in the Python orchestrator in this task)
- [x] #2 --on-error retry: either loop.py re-runs a failed iteration up to --retry-count times AND a new pytest test asserts the retry occurs, or the retry choice/flag is removed from args.py and its SKILL/CLAUDE docs
- [x] #3 --log-file: either the loop/tools consume it AND a new pytest test asserts log output is written to the given path, or --log-file is removed from args.py and its SKILL/CLAUDE docs
- [x] #4 task-summary-count warning and current_task null-clearing: each is either implemented in loop.py with a passing pytest test asserting the behavior, or documented in the task notes as an intentional simplification
- [x] #5 A coverage map in the task notes lists every behavior the TASK-199-retired bats files pinned and maps each to the owning pytest test(s); any behavior with no pytest owner is either newly covered in this task or explicitly declared intentional-drop — no entry left 'uncovered'
- [x] #6 tests/integration/usage-pause.bats no longer references the dead RALPH_USAGE_CHECK_SCRIPT/usage-check.sh path (repointed to the Python usage check or the stale tests removed)
- [x] #7 uv run pytest passes with test count >= 185 (reflecting any newly added tests) and uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From TASK-199 review (task-reviewer): also audit the stale reference tests/integration/usage-pause.bats:110 RALPH_USAGE_CHECK_SCRIPT -> plugins/ralph/skills/ralph-run/scripts/usage-check.sh (untracked; ported to Python in task-151). The survivor tests pass via ccusage mocks, but the path is dead and should be repointed or removed.

Plan (autonomous): Triage classifies all 4 deltas as REAL-GAP and restores bash parity (each has a TASK-199-retired bats spec + clear semantics). loop.py: (1) retry loop re-invokes tool on non-timeout failure when on_error=retry within retry_count, exhaustion stops (bash 796-836/647-655); (2) --log-file appends '[ts] ERROR: Iteration N failed... (tool,retry)' per failed attempt (bash log_error 614-624); (3) task-summary-count warning to stderr when count!=1 & not COMPLETE, fires on timeout/continue (bash 838-843); (4) current_task re-derived from 'backlog task list -s In Progress' after each non-stopping iteration (bash 849). tasks.py: add current_in_progress_task(). New pytest test_loop_deltas.py covers all 4; patch current_in_progress_task in 5 loop fixtures for hermeticity. AC#6: drop dead RALPH_USAGE_CHECK_SCRIPT/usage-check.sh export in usage-pause.bats. AC#5: coverage map in notes.

CLASSIFICATION (AC #1, #4) - all 4 deltas triaged as REAL-GAP and implemented in this task (bash parity restored; each had a TASK-199-retired bats spec):
1. --on-error retry / --retry-count -> REAL-GAP. Before: loop.py treated retry identically to continue (never re-ran). After: loop.py _invoke_tool_with_retry re-runs a failed (non-timeout) iteration up to --retry-count times; a later success is not counted/recorded; exhaustion records one failure and STOPS (bash ralph.sh:796-836,647-655). Timeouts never retry.
2. --log-file -> REAL-GAP. Before: parsed but a silent no-op. After: loop.py _append_error_log appends '[ts] ERROR: Iteration N failed with exit code X (tool: T, retry: A)' to the path per failed attempt (bash log_error ralph.sh:614-624); empty path is a no-op.
3. task-summary block-count warning -> REAL-GAP. Before: signals.task_summary_count computed but never emitted. After: loop.py _warn_task_summary_count prints 'WARNING: Iteration N produced X ...Task Summary... blocks (expected 1)...' to stderr when count is not 1 and no COMPLETE sentinel; fires on timeout/continue exits too (bash ralph.sh:838-843).
4. current_task null-clearing -> REAL-GAP. Before: current_task stuck at last-picked task. After: tasks.py current_in_progress_task() re-derives from 'backlog task list -s In Progress' and loop.py updates status.current_task after every non-stopping iteration, nulling it once the picked task moves to Done (bash ralph.sh:849). Stop paths keep the picked task (bash exits before re-derive).

COVERAGE MAP (AC #5), part 1 - the 4 gap behaviors + removed cross-file tests, now owned by pytest:
[one-task-enforcement.bats -> NEW test_loop_deltas.py] 0 blocks warn=test_warn_task_summary_count[0-False-True]; 2 blocks warn=[2-False-True]; exactly-1 no-warn=[1-False-False]; timeout+0 warn=test_summary_warning_fires_on_timeout; COMPLETE+0 no-warn=[0-True-False] and test_no_summary_warning_on_completion.
[run-summary-integration.bats retry test -> NEW] retry-that-succeeds=0 failed/0 errors=test_retry_success_zero_failed_iterations_zero_errors; exhaustion=test_retry_exhausted_stops_with_error.
[status-file-integration.bats current_task+log-file -> NEW] current_task null when no In Progress=test_current_task_nulled_when_no_in_progress and test_current_task_reflects_in_progress and test_tasks::test_current_in_progress_task_returns_first_id/_none_when_empty; log-file flag=test_log_file_receives_error_line and test_append_error_log_empty_path_is_noop and test_append_error_log_writes_expected_format.
[status-file-integration.bats run-log tests] run log created/contains iteration output/contains summary -> test_loop_run_log::test_run_log_created_and_grows_across_iterations and test_run_log_respects_RALPH_RUN_LOG_override.
[on-error-continue.bats removed 2] executes all iterations after failures -> test_on_error_continue_does_not_retry and test_loop_exit_code::test_max_iterations_zero_completions_returns_1; FAILED_ITERATIONS count matches -> test_loop_exit_code::test_max_iterations_completion_plus_failure_returns_1 and test_retry_exhausted_stops_with_error.
[usage-pause.bats removed 1] per-iteration warn once -> usage.check_and_pause once-only guard + surviving usage-pause.bats test 4 (repointed off dead usage-check.sh env in AC #6).

COVERAGE MAP (AC #5), part 2 - fully-deleted bats files already owned by the pre-existing pytest suite (TASK-199 thesis):
[argument-validation.bats] -> test_orchestrator_args.py (test_parse_defaults_match_bash, test_parse_intermixed_supports_positional_anywhere, test_validate_rejects_unknown_tool/effort/zero_timeout/negative_retry_count/non_numeric_tasks/missing_prompt_file, test_validate_accepts_present_prompt_file/well_formed_tasks/fractional_timeout, test_validate_rejects_tasks_and_prompt_file_together).
[status-file.bats] -> test_status.py (test_golden_roundtrip_byte_identical, test_write_atomic_creates_file/overwrites_existing/leaves_no_temp_files, test_extra_field_rejected).
[run-summary.bats] -> test_summary.py (test_print_summary_contains_all_labels, test_format_duration_hours_minutes_seconds, test_print_summary_omits_per_iteration_block_when_empty, test_exit_reasons_are_the_closed_set, failed-iteration count via test_loop_exit_code).
[usage-check.bats] -> test_usage_check.py (test_buffer_zero_short_circuits, test_active_block_within/outside_buffer, test_inactive_block_returns_0, test_ccusage_missing/nonzero_returns_2, test_unparseable_json/endtime_returns_2, test_missing_endtime_returns_2, test_non_numeric/empty_buffer_returns_2, test_cli_writes_sentinel_on_exit_2).
[dependency-checks.bats] -> test_preflight.py (test_success_path, test_no_todo_tasks_fails, test_devcontainer_missing_fails, test_ralph_not_executable_fails, test_ralph_syntax_error_fails).
[interrupt-trap.bats] -> test_loop_signal_interrupt.py (test_handler_forwards_sigterm/sigint_to_active_subprocess_pgroup, test_orchestrator_exits_promptly_on_sigterm; state=failed via loop _finalize covered there) + RUN_LOG retention via test_loop_run_log.
[timeout-handling.bats] -> timeout warning/continue-next-iter/exit-124 = test_retry_not_applied_to_timeout + loop timeout branch + _subprocess.TIMEOUT_EXIT_CODE; normal-exec = all test_loop_* happy paths; timeout+completion-stops = completion-signal.bats survivor + loop complete-check; invalid/fractional timeout = test_orchestrator_args::test_validate_rejects_zero_timeout/_accepts_fractional_timeout.
INTENTIONAL-DROP (only one, not a behavior gap): timeout-handling.bats 'Temp file cleaned up on normal exit/timeout/error'. The Python port uses per-iteration tempfile.mkstemp kept as ToolResult.stdout_path for post-mortem grep (documented in tools/__init__.py), reaped by the OS temp dir, instead of bash's single OUTFILE rm-trap. Deliberate design of the port (predates this task); no pytest owner by design. No entry left uncovered.

Commit: `f909110` - task-200: Restore retry, --log-file, task-summary warning, and current_task null-clearing in the Python orchestrator loop

Done: task-reviewer APPROVED (independent bash-parity cross-check vs the 895-line pre-retirement ralph.sh @ 1cd3720^; all 7 ACs + 8-item checklist + R1-R16 pass). Final gate: uv run pytest = 204 passed (baseline 185, +19), uv run ruff check . = clean, bats integration+unit = 96 passed. Implemented in commit f909110.
<!-- SECTION:NOTES:END -->
