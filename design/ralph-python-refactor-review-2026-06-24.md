# Feature Review: ralph-python-refactor (delta: TASK-175 + TASK-176)

Date: 2026-06-24
Scope: delta review of the two tasks landed since the prior cumulative reviews (2026-06-22, -01, -02). TASK-149..164 alignment is established in those prior reviews; this review is a focused delta on the post-Phase-C-flip bash-parity gap fixes.

**Verdict: Aligned**

**Passes run:** 1, 2, 3, 4, 5
**Passes skipped:** none — both PRD and brainstorm are present in the bundle, both have Non-Goals and Success Metrics sections.

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-11 | Orchestrator MUST work both in-devcontainer (via `--devcontainer`) and on the host; devcontainer wrapping argv MUST be a list, never a joined string | Delivered (gap closed) | `skills/ralph-run/scripts/ralph/devcontainer.py` lines 31-45 assemble `["devcontainer","up","--workspace-folder",str(workspace_folder)]` as a Python list; `loop.py:121-124` invokes pre-status-init when `args.devcontainer` true. This was a pre-existing gap in FR-11 coverage (only `exec` was wrapped; `up` was missing) and is now closed. |
| FR-1 (run log adjacent) | Byte-identical on-disk artifacts including `backlog/.ralph-run.log` format | Delivered | `loop.py:_run_log_file_path` honors `RALPH_RUN_LOG` env override with project-rooted default (matches `ralph.sh:461`); `_truncate_run_log` zero-bytes the file at startup (matches `ralph.sh:692` `: > "$RUN_LOG"`); `tools/_subprocess.py:_stream_to_tee` appends each line to the run-log in addition to the per-iteration tempfile (line-by-line streaming, parity with `exec > >(tee -a "$RUN_LOG")`). |
| FR-12 | `RALPH_PROJECT_ROOT` env var MUST be honored for all project-relative path resolution | Delivered | `_run_log_file_path` uses `project_root / "backlog" / ".ralph-run.log"`, which inherits the `RALPH_PROJECT_ROOT`-resolved project_root from the entry point (no regression). Test `test_loop_run_log.py:test_run_log_respects_RALPH_RUN_LOG_override` pins it. |
| US-007 cutover gate row "no leftover claude-code/python/uv processes" | Delivered (parity-preserving) | TASK-175 reproducer execution confirmed in task notes: `state=completed`, `exit_code=0`, container went from "Exited (0)" → "Up 9 seconds" — orchestrator no longer crashes on iteration 1 in default-python + devcontainer config. |
| Cumulative review reviewer cross-check: "ralph-status and ralph-status-watch render Python-written status JSON identically to bash-written" | Delivered (indirect — preserved) | TASK-176 implementation note "wait_heartbeat.py:73 is unchanged; '(run log not created)' no longer appears" closes the failure-path diagnostic regression. No status JSON schema touched. |

## Non-Goal Violations

None detected.

Cross-checked the PRD §5 Non-Goals list against the diff:
- No schema changes to `backlog/.ralph-status.json` — confirmed; `StatusFile` model not modified
- No new CLI flags / no flag renames — confirmed; no argparse touched
- No new sentinels — confirmed; signals.py untouched
- No new retry policy — confirmed
- No worktree / external reviewer / notifications / `--plan` mode — confirmed
- No hook changes — confirmed
- No `sync.sh` / `utc-to-moscow.sh` / `init-firewall.sh` changes — confirmed
- No `pyproject.toml` `[project]` section / no `uv.lock` — confirmed
- No structured `logging` migration — confirmed; new code uses `print()` for parity strings and best-effort I/O for log writes
- No Python version upgrade — confirmed

## Scope Cut Violations

None detected.

Brainstorm cut "Improvements come later" / strict-port discipline:
- **One minor deviation worth flagging as a follow-up note (not a violation):** the Python `start_devcontainer` returns the CLI exit code on `up` failure and the orchestrator aborts before status init. Bash `ralph.sh:602-611` does NOT check the exit code of `devcontainer up` — it always prints "Devcontainer is ready." and continues into the loop. The Python is **stricter** than bash, not weaker. This is explicitly sanctioned by TASK-175 AC #4 ("orchestrator exits non-zero with devcontainer CLI stderr surfaced; iteration loop is NOT entered"), so the task contract authorizes the deviation, but it is a small intentional crack in strict-byte-parity that should be acknowledged. The task-reviewer note about `capture_output=True` buffering also documents a streaming-vs-batch deviation in the success path (silent pause during image build).

## Success Metric Assessment

| Metric | Status | Notes |
|--------|--------|-------|
| 5 consecutive clean Python runs (cutover gate) | Hypothesis | Out of scope for this delta (handled under TASK-156). TASK-175/176 are gap fixes that make those 5 runs achievable in default-python + devcontainer mode. AC #2 of TASK-175 was verified live (one clean run); the remaining four are TASK-156's responsibility. |
| `check_run_clean.py --run-only` exit 0 on each gating run | Hypothesis | Same — gate harness lives in TASK-156's scope; TASK-175/176 unblock the harness's ability to run cleanly in the canonical config. |
| `pyright` and `ruff check` pass before every task-reviewer invocation | Measurable | Both task notes explicitly record "ruff clean on all 5 changed files" (TASK-176) and "ruff clean" (TASK-175). pyright not called out in the task notes but is part of the standing project gate (FR-15). |
| All unit tests + 1 E2E test pass | Measurable | TASK-175 notes "All 207 pytest tests pass"; TASK-176 notes "Full suite: 209/209 passed". The +2 delta corresponds to the new `test_loop_run_log.py` cases. TASK-175 also adds two new test modules (`test_devcontainer.py` 3 unit + `test_loop_devcontainer_up.py` 3 integration) — the count delta from 207→209 between TASK-175 done and TASK-176 done is internally consistent. |
| Zero behavior regressions caught by ralph-reviewer cumulative review | Measurable — this review | Verdict here is Aligned with one minor strict-port deviation acknowledged (devcontainer up failure handling is tighter than bash). No regression to existing parity contract. |

## Drift List

No drift detected.

Every hunk in the diff traces directly to one of:
- TASK-175 AC #1, #4, #5 (new `ralph/devcontainer.py`, `loop.py:121-124` pre-status invocation, `tests/test_devcontainer.py`, `tests/test_loop_devcontainer_up.py`)
- TASK-176 AC #1, #2, #4, #5, #8 (`loop.py:_run_log_file_path` + `_truncate_run_log`, `tools/_subprocess.py:execute` extended with `run_log_path`, `tools/_subprocess.py:_stream_to_tee` line-by-line dual-write, `tools/claude.py` + `tools/opencode.py` constructor plumbing, `tests/test_loop_run_log.py`)
- Backlog task files for TASK-175 and TASK-176 themselves

The constructor-signature additions on `ClaudeTool`/`OpencodeTool` (`run_log_path` parameter) are minimal infrastructure plumbing directly supporting AC #2 of TASK-176; not creep.

## Reviewer Notes

**Strict-port semantics check (TASK-175 placement):** confirmed correct. `loop.py:121-124` invokes `start_devcontainer` BEFORE `_status_file_path`/`_heartbeat_file_path`/`StatusFile()` construction. The early `return rc` on failure exits without ever calling `status.write_atomic()` — so a failed `up` leaves no status JSON on disk. This is desirable for two reasons: (1) it matches the bash invocation order (devcontainer up happens at line 603, well before line 692 where `: > "$RUN_LOG"` runs); (2) it prevents an orphan `state=running` status file from confusing `ralph-status` after a failed bootstrap. The integration test `test_loop_devcontainer_up.py:test_up_failure_returns_nonzero_and_skips_tool` pins both invariants (rc==2, no `tool.run` call).

**Strict-port semantics check (TASK-176 path resolution):** confirmed correct. `_run_log_file_path` reads `RALPH_RUN_LOG` env var first, falls back to `project_root / "backlog" / ".ralph-run.log"`. This mirrors `ralph.sh:461`: `RUN_LOG="${RALPH_RUN_LOG:-${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}/backlog/.ralph-run.log}"`. The Python derives `project_root` from `RALPH_PROJECT_ROOT`-or-fallback upstream (entry point), so the composed precedence is identical. `test_run_log_respects_RALPH_RUN_LOG_override` pins the env precedence and confirms the default path is NOT touched when the override is set.

**Test contract depth (not smoke):**
- TASK-175's `test_loop_devcontainer_up.py` uses a call-log spy to assert ordering (`["start_devcontainer", "tool.run"]`), not just "both got called." This is a genuine ordering pin.
- TASK-176's `test_run_log_created_and_grows_across_iterations` uses `task_done_no_summary` fake-claude mode deliberately so iter 1 doesn't short-circuit via COMPLETE — this is a deliberate test-construction choice that exercises the multi-iteration append path. The banner-count==2 assertion plus the per-iteration TASK-ID assertion gives strong evidence that the file is appended (not overwritten) and that BOTH iterations' stdout actually reaches the file. Not smoke.
- One small caveat: AC #3 ("file size after iteration 2 strictly greater than after iteration 1") is asserted at the e2e layer indirectly via banner-count==2 rather than by sampling size at iter-1 boundary and iter-2 boundary separately. The task notes acknowledge this as "strict reading of AC #3 at the e2e layer." Functionally equivalent for the parity contract; a future regression that overwrites iter-2 over iter-1 would still trip banner-count==2 because the second banner wouldn't be there. Acceptable.

**One strict-port deviation worth tracking (informational, not blocking):** Python's `start_devcontainer` aborts the orchestrator on non-zero `devcontainer up` exit; bash continues regardless. This is a behavior delta in a strict-port window. The task AC #4 explicitly sanctions it (and arguably it's the safer behavior), but it is the kind of "improvement during the port" that brainstorm Q2 said to defer. Recommend filing as a one-line note in the cutover (TASK-156 / US-007) summary so the cumulative reviewer at final cutover sees it pre-disclosed rather than discovering it. Same for the `capture_output=True` buffering observation already captured by the task-reviewer in TASK-175's notes.

**Cumulative posture:** the two delta tasks tighten the strict-port contract in the canonical default-python + devcontainer configuration without expanding scope, introducing schema fields, or changing the CLI surface. Both gaps were the kind of late-discovered "bash side-effect we didn't notice until we ran it for real" that the dual-running window in brainstorm Stage 3 was specifically designed to surface. The fact that they were found, scoped narrowly, fixed under their own backlog tasks, covered by genuine ordering / size / env-override tests, and merged into master without disturbing TASK-156's pending cutover is exactly the migration plan working as designed.
