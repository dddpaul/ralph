# Feature Review: ralph-python-refactor

**Date:** 2026-06-22
**Reviewer:** ralph-reviewer agent
**Diff range:** `1cd300b..HEAD` (8 Done tasks: 149, 150, 151, 152, 153, 154, 155, 158)
**Verdict: Partial**

**Passes run:** 1, 2, 3, 4, 5
**Passes skipped:** none — both PRD and brainstorm exist; PRD has Non-Goals, Success Metrics, and clearly enumerated requirements.

The "Partial" verdict reflects the explicit scope split: tasks 149–155 + 158 land the entire strangler-fig stack (US-000 through US-006); cutover (US-007 / TASK-156) is deliberately deferred and so leaves a meaningful share of FRs in "Partial" status. Up to the strangler stage, the work is aligned with intent. Two parity-gap follow-ups (TASK-159, TASK-160) are correctly filed as new tasks rather than smuggled into the port.

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| US-000 | ralph-sync nested-dir spike | Delivered | TASK-149 notes — sync.sh:47 (`diff -rq`) + sync.sh:115/119-120 (`cp -r`) are recursive; works as-is, no fix needed |
| US-001 | Scaffold + StatusFile pydantic | Delivered | `skills/ralph-run/scripts/ralph_orchestrator.py` (PEP 723), `ralph/status.py:36-56` (21 fields in bash order, including all 5 `paused_*`), `ralph/status.py:62-82` (atomic write via NamedTemporaryFile + `os.replace`), `tests/test_status.py`, `pyproject.toml` (tool-only) |
| US-002 | Helpers ported | Delivered | `ralph/preflight.py`, `ralph/wait_heartbeat.py`, `ralph/usage_check.py` + 3 parity test suites (`test_preflight_parity.py`, `test_wait_heartbeat_parity.py`, `test_usage_check_parity.py`); exit-code contract 0/1/2 preserved |
| US-003 | Core internals | Delivered | `ralph/signals.py`, `ralph/tasks.py`, `ralph/heartbeat.py` (daemon thread + threading.Event + bounded join), `ralph/usage.py`, `ralph/tools/__init__.py` (Tool ABC + ToolResult); golden fixtures under `tests/fixtures/signals/` |
| US-004 | claude-code subprocess + cleanup | Partial | `ralph/tools/claude.py` + `ralph/tools/_subprocess.py` implement Popen + `start_new_session=True` + line-by-line queue + tee + timeout→pgroup SIGTERM/SIGKILL. AC #5 (the orchestrator-side SIGTERM handler that kills the active subprocess group) is **explicitly deferred** in TASK-153 notes and filed as TASK-160. Currently the `_SignalInstaller` in `loop.py:213-241` polls between iterations only — a SIGTERM during `tool.run()` waits for the iteration timeout. |
| US-005 | Opencode + entry point + E2E | Partial | `ralph/tools/opencode.py`, `ralph_orchestrator.py`, `ralph/args.py` (allow_abbrev=False + parse_intermixed_args + 11 flags + positional), `ralph/loop.py` (within-iteration ordering matches AC #5), `ralph/prompts.py` (MODE: prefix + prompt-file replacement), `tests/fixtures/fake_claude.py` (4 modes), `tests/test_e2e_fake_claude.py`. Two parity gaps acknowledged in TASK-154 notes and filed as TASK-159 + TASK-160 (max-iterations exit-code divergence; signal-handler latency). |
| US-006 | Strangler integration + R11 mirror | Delivered | Live `ralph.sh` (10-line dispatch on `RALPH_IMPL`), `skills/ralph-init/templates/root/ralph.sh` (byte-identical), `.devcontainer/Dockerfile` (lines 97-102 unconditional uv + Python 3.14 install), `skills/ralph-init/templates/devcontainer/Dockerfile.base` (mirror with the required inline comment), `skills/ralph-init/SKILL.md` Prerequisites section, `skills/ralph-run/SKILL.md` `impl=` parameter |
| US-007 | Cutover + cleanup + downstream upgrade | Missing | TASK-156 still To Do, no `tests/scripts/check_run_clean.py`, inner bash `ralph.sh` + 3 bash helpers still present. **By design — the prompt confirms this is the expected state.** |
| FR-1 | Byte-identical status JSON schema, 18 fields, same order | Delivered | `ralph/status.py:36-56` declares fields in the exact order emitted by `ralph.sh:412` (the bash `cat <<EOF` JSON line); golden-file round-trip test confirms byte-equality |
| FR-2 | Exact CLI flag set, no auto short-flags, no new flags | Delivered | `ralph/args.py:55-71` (all 11 long flags + positional, `allow_abbrev=False`, `parse_intermixed_args`) |
| FR-3 | Status JSON writes atomic | Delivered | `ralph/status.py:62-82` |
| FR-4 | Heartbeat touch every 5s + EXIT cleanup | Delivered | `ralph/heartbeat.py` (daemon thread, threading.Event, file unlink in `stop()`) + context-manager use in `loop.py:135` |
| FR-5 | Per-iteration timeout, exit 124 = continue | Delivered | `ralph/tools/_subprocess.py` + `loop.py:_run_loop` treats `TIMEOUT_EXIT_CODE` as continuation (records to errors, increments `failed_iterations`, but does NOT respect `--on-error stop` — matches bash) |
| FR-6 | SIGTERM/SIGINT kill entire process group + summary prints | Partial | Tool-level pgroup cleanup is in place (`_subprocess.py` + `tools/claude.py`). Orchestrator-level signal handler currently only polls between iterations, not mid-`tool.run()`. Filed as TASK-160. Summary IS printed on every exit path via the `finally` block in `loop.run`. |
| FR-7 | Run summary, closed-set exit_reason | Partial | `ralph/summary.py:14` defines `EXIT_REASONS` as the closed set; `loop.py:162` asserts membership. **Minor drift:** the paused-exit path at `loop.py:193` tags `exit_reason = "all tasks done"` so it can pass the closed-set assertion. The run summary then prints "Exit reason: all tasks done" even when the run actually paused due to usage cap — a strict-port deviation worth flagging (the bash summary distinguishes; see `ralph.sh:304-334`). |
| FR-8 | MODE: prefix verbatim | Delivered | `ralph/prompts.py` (`build_prompt`) |
| FR-9 | `<promise>COMPLETE</promise>` + anchored `^## Task Summary$` | Delivered | `ralph/signals.py` + `tests/fixtures/signals/*.txt` golden fixtures (including the `inline_summary_not_anchored.txt` case) |
| FR-10 | Strangler dispatch via RALPH_IMPL, default bash | Delivered | `ralph.sh:7` (`if [ "${RALPH_IMPL:-bash}" = "python" ]`) and matching template |
| FR-11 | Devcontainer wrap argv is a list, never joined | Delivered | `ralph/tools/claude.py` + `ralph/tools/opencode.py` build argv as `list[str]`; test in `test_tool_claude.py` |
| FR-12 | `RALPH_PROJECT_ROOT` honored + fallback | Delivered | `ralph_orchestrator.py:29-38` |
| FR-13 | Usage-cap exit-code contract + 5 paused_* fields | Delivered | `ralph/usage.py:79-115` mutates all 5 fields; `ralph/usage_check.py` preserves 0/1/2 + sentinel flag file; `loop.py:187-195` flips `state=paused` |
| FR-14 | `--tasks` whitelist semantics | Delivered | `ralph/args.py:_TASKS_RE` (numeric only), `ralph/tasks.py:pick_next_task(whitelist=...)`, `args.py:117-122` enforces mutual exclusion with `--prompt-file`; per-iteration re-query in `loop.py:_run_loop` |
| FR-15 | pyright + ruff pass | Delivered | All task notes report `uv run pyright skills/ralph-run/scripts` 0 errors and `ruff check` clean; pyproject.toml configures strict mode for the path |
| FR-16 | R11 mirror of two template files | Delivered | TASK-155 + TASK-158: live shim & Dockerfile + matching templates in `skills/ralph-init/templates/root/ralph.sh` and `templates/devcontainer/Dockerfile.base` |

## Non-Goal Violations

None detected. Spot checks of the explicit non-goals:

- **No schema changes** to `.ralph-status.json` — `ralph/status.py` declares the bash 21 fields in the bash order; no additions; `ConfigDict(extra="forbid")` enforces this both ways.
- **No new CLI flags** — `ralph/args.py` is a strict copy of the bash flag set (verified against `ralph.sh` arg-parsing block).
- **No new sentinels** — `ralph/signals.py` parses only `<promise>COMPLETE</promise>` and anchored `^## Task Summary$`.
- **No `pyproject.toml` `[project]` section** — `pyproject.toml` uses `[dependency-groups]` (PEP 735) and `[tool.uv]` instead, plus only `[tool.ruff]`, `[tool.pyright]`, `[tool.pytest.ini_options]`.
- **No `uv.lock`** — `.gitignore` includes `uv.lock`; no lock file in the diff.
- **No hook changes** — diff does not touch `.claude/hooks/*.sh` or `templates/git-hooks/*`.
- **No `sync.sh` changes** — TASK-149 confirmed sync works as-is; no edits to `sync.sh` in the diff.
- **No `init-firewall.sh` or `utc-to-moscow.sh` changes** — neither file appears in the diff.
- **No CI pipeline** — no `.github/workflows/` adds.
- **No structured logging migration** — `loop.py` and friends use `print()`; only minor `with suppress(...)` patterns instead of full logging.

## Scope Cut Violations

None detected. Brainstorm explicitly cut the following; none are present:

- §6.1 richer sentinel taxonomy — not implemented.
- §6.2 external/cross-model reviewer — not implemented.
- §6.3 worktree isolation — not implemented.
- §6.4 pattern-based retry classification — `args.py:_ON_ERROR_CHOICES` is still the 3-option set `stop|continue|retry`.
- §6.5 `--plan` mode — not added.
- §6.6 notifications — not added.

## Success Metric Assessment

| Metric | Status | Notes |
|--------|--------|-------|
| 5 consecutive clean Python runs before flip | Unmeasurable yet | Deferred to US-007 / TASK-156. `check_run_clean.py --run-only` does not exist in the diff — but it is explicitly part of TASK-156 AC #1, so absence at this stage is expected. |
| 5 more clean runs post-flip | Unmeasurable yet | Same — part of TASK-156 burn-in. |
| `check_run_clean.py --run-only` exit 0 on each gating run | Unmeasurable | Script absent. Will need TASK-156. |
| `check_run_clean.py --parity bash.json python.json` schema parity | Hypothesis only | The golden-file round-trip test (`test_status.py`) plus the existing fixtures already covers schema parity for the writer side; a separate `--parity` mode would only be useful for cross-implementation diffing during the dual-run window. Currently absent; deferred to TASK-156. |
| pyright + ruff pass before every task-reviewer call | Measurable post-merge | All 6 task notes (TASK-149 through TASK-155, TASK-158) explicitly record green pyright/ruff/pytest. |
| All unit + 1 E2E test pass via `uv run pytest` | Measurable post-merge | 178 tests passing per TASK-154 + TASK-155 notes; E2E test at `tests/test_e2e_fake_claude.py` exists. |
| Zero behavior regressions per ralph-reviewer | Pending | This very review. Final pre-cutover sweep should re-run after TASK-159 + TASK-160 land. |
| ralph-sync directory propagation works | Measurable post-merge | TASK-149 records empirical pass. |

## Drift List

The following are minor strict-port deviations or smells worth tracking; none rise to "shipping non-goal content," but several are worth filing as small follow-ups before TASK-156:

- **`skills/ralph-run/scripts/ralph/loop.py:193`** — On the usage-cap paused path the code tags `state.exit_reason = "all tasks done"` to satisfy the closed-set assertion at `loop.py:162`. The user-visible run summary then prints `Exit reason: all tasks done` even though the run paused at the usage cap (bash's `paused` is a terminal state distinct from completion). Two clean fixes: (a) extend `EXIT_REASONS` with `"paused"` and add a `"paused"` branch in `summary.py`; or (b) leave the in-status `state="paused"` but emit a separate "paused at block-end" summary line. Either way, the current label is a strict-port deviation from bash's summary text.
- **`skills/ralph-run/scripts/ralph_orchestrator.py:38`** — `Path(__file__).resolve().parent` returns the script's directory (`skills/ralph-run/scripts/`), not the project root. This matches the literal AC wording ("`Path(__file__).parent` fallback") but functionally diverges from bash's `SCRIPT_DIR` semantics, which in the bash case **is** the project root because of how the outer shim exports `RALPH_PROJECT_ROOT` first. Live invocation always sets the env var so this only bites a standalone `uv run ralph_orchestrator.py` invocation — but worth noting because the bash fallback would land in the inner script dir under `~/.claude/skills/ralph-run/scripts/`, which is also not a project root. Equivalent behaviors, equivalently wrong as a standalone fallback; not a regression.
- **`skills/ralph-run/scripts/ralph/loop.py:213-241`** (`_SignalInstaller`) — The orchestrator's SIGTERM handler only triggers at iteration boundaries via `raise_if_pending()`. Bash's trap (`ralph.sh:582-593`) `pgrep -P $$ | xargs -n1 kill -TERM` kills the active child immediately. Already filed as TASK-160 — well-handled, just confirming.
- **`skills/ralph-run/scripts/ralph/loop.py:_run_loop`** — On the `max iterations reached` path, the orchestrator always returns `exit_code=0`, while bash returns 1 when `TASKS_COMPLETED==0 || FAILED_ITERATIONS>0` (`ralph.sh:889-894`). Already filed as TASK-159.
- **Bash helpers still live alongside Python helpers** — `preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`, and the inner `ralph.sh` are still in `skills/ralph-run/scripts/`. Expected and correct for the dual-running window; their removal is TASK-156's job. Flagged only so the cutover task knows the exact set to delete.
- **Test surface includes types-of bash subprocess parity tests** (`test_preflight_parity.py`, `test_usage_check_parity.py`, `test_wait_heartbeat_parity.py`) that will go stale once bash is deleted. Consider what TASK-156 does with them — either retire them with the bash helpers, or keep them as historical parity artifacts. Not in scope for this review; noted for the cutover.

No hunks outside the PRD/brainstorm scope were found. The Dockerfile and outer-shim edits, the SKILL.md additions, and the new tasks (TASK-157 for the `--strict` flag cleanup; TASK-158 for the precondition split-out; TASK-159/160 for parity gaps) are all traceable to PRD requirements or to operator-driven scope adjustments documented in the task notes.

## Reviewer Notes

- **Strict-port discipline is well-respected.** The Python code reads as a faithful translation rather than a redesign. Field order in `StatusFile`, the closed-set `EXIT_REASONS`, the `MODE:` prefix builder, the devcontainer argv-as-list invariant, and the heartbeat 5s/15s threshold are all directly mappable to the bash source. The R16-style historical-context appendix is referenced only when necessary.
- **The TASK-153/154/155 chain correctly defers cross-task concerns.** TASK-153 noted AC #5 (orchestrator SIGTERM handler) belongs to US-005; TASK-154 then implemented the polling shape and filed the latency gap as TASK-160 rather than smuggling fixes. The discipline avoids the typical "while I was there..." scope-bloat antipattern.
- **TASK-157 (pyright `--strict` cleanup) and TASK-158 (devcontainer precondition split-out) are well-handled mid-flight discoveries.** Both are documented as wrapper tasks rather than silent edits to in-flight ACs. The TASK-155 dependency edit (replace vs. add for `--dep`) was caught by the task-reviewer and corrected; that's exactly the watchful loop the rubric is designed to encourage.
- **One pre-cutover thing worth doing before TASK-156:** consider whether `EXIT_REASONS` should grow `"paused"` (or whether `loop.py:193`'s `"all tasks done"` reuse is acceptable as a strict port). Bash's summary distinguishes these textually; the Python version currently does not. A 5-line follow-up task would close it; not a blocker for the cutover gate per se, but worth landing before the 5-clean-runs counter starts.
- **Test coverage is good.** 178 tests including 1 E2E (`test_e2e_fake_claude.py`) + 3 parity test suites against the bash helpers. The `tests/fixtures/fake_claude.py` shim correctly drives the orchestrator end-to-end (success mode actually edits the backlog via the on-PATH backlog mock, exercising the done-task diff).
- **What's NOT yet done (and correctly so):** `tests/scripts/check_run_clean.py`, the 5+5 clean-run operator-driven verification, inner-bash deletion, `CLAUDE.md` project-language line tightening, downstream-upgrade communication. All of these are TASK-156 work. The "Partial" verdict on this review is the appropriate signal that the feature is on track but the cutover gate has not yet been exercised.

**Recommended next steps before TASK-156:**
1. Land TASK-159 (max-iter exit code) and TASK-160 (signal-handler latency) — both are explicitly called out as parity gaps to close BEFORE US-007.
2. Optionally file a small "paused exit_reason vocabulary" task if the strict-port deviation at `loop.py:193` matters to you.
3. Then proceed with TASK-156 cutover, starting the 5-clean-runs counter.
