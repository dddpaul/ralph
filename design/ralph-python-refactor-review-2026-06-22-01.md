# Feature Review: ralph-python-refactor (review #2)

**Date:** 2026-06-22
**Reviewer:** ralph-reviewer agent
**Diff range:** `1cd300b..HEAD` (11 Done tasks: 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 161)
**Prior review:** `design/ralph-python-refactor-review-2026-06-22.md`
**Verdict: Partial**

**Passes run:** 1, 2, 3, 4, 5
**Passes skipped:** none — PRD and brainstorm both exist; PRD has Non-Goals, Success Metrics, and enumerated FRs.

The verdict remains **Partial** for the same structural reason as the prior review: TASK-156 (cutover, US-007) is by design still To Do. All three open drifts from the 2026-06-22 review are now **closed in code with tests**, and no new significant drift was introduced. A few latent pre-existing items are surfaced below as items the prior review missed.

---

## Status of the three prior open drifts

| Prior drift | Task | Status now | Evidence |
|---|---|---|---|
| `loop.py:193` paused exit_reason reused "all tasks done" | TASK-161 | **Closed** | `ralph/summary.py:16-18` extends `EXIT_REASONS` with `"paused"`; `ralph/loop.py:195` sets `state.exit_reason = "paused"` directly; `tests/test_loop_paused_summary.py` covers both branches; `tests/test_summary.py:10-23` pins the new closed set of 5 strings. Bash parity: `ralph.sh:724` `EXIT_REASON="paused"`. |
| SIGTERM mid-iteration latency (TASK-160) | TASK-160 | **Closed** | `ralph/loop.py:374-463` (`_SignalInstaller`): tracks active subprocess pgid; handler forwards SIGTERM to pgroup via `os.killpg`; uses `RLock` (handler may re-enter `set_active_subprocess`); race-close in `set_active_subprocess` re-fires queued SIGTERM if signal arrived before registration. Tool ABC + ClaudeTool + OpencodeTool take `on_spawn` callback. `_invoke_tool` (loop.py:292-305) wires it, clears in `finally`. E2E test `tests/test_loop_signal_interrupt.py:314-396` asserts orchestrator exits <10s after SIGTERM with `state=failed`/`exit_code=130`/`Exit reason: interrupted`. |
| Max-iterations exit code = 0 vs. bash 1 (TASK-159) | TASK-159 | **Closed** | `ralph/loop.py:288-289` sets `state.exit_code = 1` when `tasks_completed==0 OR failed_iterations>0` after the for-loop falls through. `tests/test_loop_exit_code.py` has 3 synthetic scenarios covering ACs #3-#5. Bash parity: `ralph.sh:889-894`. |
| Parity-test cleanup decision (added to TASK-156) | TASK-156 AC #13 | **Closed (as planned)** | AC #13: "Parity test suites (test_preflight_parity.py, test_wait_heartbeat_parity.py, test_usage_check_parity.py) deleted alongside the bash helpers — they cannot pass once the bash side is gone." |

---

## Intent → Implementation Matrix (delta vs. prior review)

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| US-000 | sync nested-dir spike | Delivered | unchanged |
| US-001 | Scaffold + StatusFile | Delivered | unchanged |
| US-002 | Helpers ported | Delivered | unchanged |
| US-003 | Core internals | Delivered | unchanged |
| US-004 | claude subprocess + cleanup | **Delivered (was Partial)** | AC #5 (orchestrator SIGTERM handler kills active subprocess group) now lives in `_SignalInstaller` after TASK-160. |
| US-005 | Opencode + entry point + E2E | **Delivered (was Partial)** | Both deferred parity gaps closed: max-iter exit code (TASK-159), signal-handler latency (TASK-160). E2E test now also covers the signal path. |
| US-006 | Strangler integration + R11 mirror | Delivered | unchanged |
| US-007 | Cutover + cleanup + downstream upgrade | Missing (by design) | TASK-156 still To Do; `tests/scripts/check_run_clean.py` absent; inner bash `ralph.sh` + 3 helpers still present. Expected end state of this review cycle. |
| FR-1 | Byte-identical status JSON | Delivered | unchanged |
| FR-2 | Exact CLI flag set | Delivered | unchanged |
| FR-3 | Atomic status writes | Delivered | unchanged |
| FR-4 | Heartbeat 5s + EXIT cleanup | Delivered | unchanged |
| FR-5 | Per-iter timeout, exit 124 = continue | Delivered | unchanged |
| FR-6 | SIGTERM kills whole process group + summary prints | **Delivered (was Partial)** | `_SignalInstaller._handler` (loop.py:456-463) forwards SIGTERM to active child's pgroup via `os.killpg`, mirroring bash's `_kill_children`. Summary still printed on every exit path via `finally`. |
| FR-7 | Run summary, closed-set exit_reason | **Delivered (was Partial)** | Closed-set now 5 strings including `"paused"`; bash distinguishes textually too (`ralph.sh:724`). See "Latent drift" below for two minor strings still collapsed. |
| FR-8 | MODE: prefix verbatim | Delivered | unchanged |
| FR-9 | Sentinel parsing | Delivered | unchanged |
| FR-10 | Strangler dispatch | Delivered | unchanged |
| FR-11 | Devcontainer argv-as-list | Delivered | unchanged |
| FR-12 | RALPH_PROJECT_ROOT honored | Delivered | unchanged |
| FR-13 | Usage-cap exit-code contract | Delivered | unchanged |
| FR-14 | `--tasks` whitelist semantics | Partial | See drift list — `_update_after_iteration` at loop.py:319 drops the whitelist filter when recomputing `tasks_remaining`. Pre-existing; not introduced by 159/160/161. |
| FR-15 | pyright + ruff pass | Delivered | re-verified: `uv run pyright skills/ralph-run/scripts` → 0 errors; `uv run ruff check skills/ralph-run/scripts` → clean; `uv run pytest skills/ralph-run/tests/` → 191 passed in 63s on Python 3.14.4. |
| FR-16 | R11 mirror of two template files | Delivered | unchanged |

---

## Non-Goal Violations

None detected. Spot checks of the explicit non-goals all pass:

- No schema changes — `ralph/status.py` unchanged; field order and `ConfigDict(extra="forbid")` preserved.
- No new CLI flags — `ralph/args.py` unchanged.
- No new sentinels — `ralph/signals.py` unchanged.
- No new retry policy — `--on-error` still the 3-choice set.
- No `pyproject.toml [project]` — only `[tool.*]`, `[dependency-groups]`, `[tool.uv]`.
- No `uv.lock` — `.gitignore` includes `uv.lock`.
- No hook changes, no `sync.sh`/`utc-to-moscow.sh`/`init-firewall.sh` changes.

One borderline call worth recording: TASK-161 grew `EXIT_REASONS` from 4 strings to 5 (added `"paused"`). PRD §3 US-005 AC #7 literally pins the closed set as `{"all tasks done", "max iterations reached", "error", "interrupted"}`. But adding `"paused"` is actually **bash parity** (`ralph.sh:724`) and the PRD's enumerated 4 was itself an under-specification — the prior review explicitly recommended this fix. Net: bash parity beats PRD literalism; not a violation.

---

## Scope Cut Violations

None detected. Brainstorm scope cuts still respected:

- §6.1 richer sentinel taxonomy — not implemented.
- §6.2 external/cross-model reviewer — not implemented.
- §6.3 worktree isolation — not implemented.
- §6.4 pattern-based retry classification — not implemented.
- §6.5 `--plan` mode — not added.
- §6.6 notifications — not added.

---

## Success Metric Assessment

| Metric | Status | Notes |
|--------|--------|-------|
| 5 consecutive clean Python runs before flip | Unmeasurable yet | TASK-156 work. |
| 5 more clean runs post-flip | Unmeasurable yet | TASK-156 work. |
| `check_run_clean.py --run-only` exit 0 each run | Unmeasurable | Script absent. TASK-156 AC #1. |
| `check_run_clean.py --parity bash.json python.json` | Hypothesis only | Schema parity is already covered by golden-file round-trip; deferred. TASK-156 AC #2. |
| pyright + ruff pass before every task-reviewer call | Measurable post-merge | All 11 task notes record green. Re-verified fresh in this review: 0 errors. |
| All unit + 1 E2E test pass via `uv run pytest` | Measurable post-merge | **191 passed in 63s** at HEAD on Python 3.14.4 (was 178 at prior review; +8 from TASK-160, +3 from TASK-159, +2 from TASK-161). E2E test at `tests/test_e2e_fake_claude.py` + new E2E at `tests/test_loop_signal_interrupt.py::test_orchestrator_exits_promptly_on_sigterm`. |
| Zero behavior regressions per ralph-reviewer | Pending | This review. No regressions found. |
| ralph-sync directory propagation | Measurable post-merge | TASK-149 empirical pass. |

---

## Drift List

No drift introduced by TASK-159/160/161 themselves. The following are **pre-existing strict-port deviations** that survived the prior review and remain worth flagging for TASK-156:

- **`skills/ralph-run/scripts/ralph/loop.py:203`** — bash distinguishes `"all specified tasks done"` (whitelist exhausted, `ralph.sh:743`) from `"all tasks done"` (general To Do exhausted, `ralph.sh:751,881`). Python collapses both to `"all tasks done"`. Minor summary-text deviation; symmetrical to the issue TASK-161 just fixed for `"paused"`. A 5-line extension of `EXIT_REASONS` + a one-line branch at loop.py:203 would close it.
- **`skills/ralph-run/scripts/ralph/loop.py:288-289`** — when the for loop falls through, `state.exit_reason` stays at its default `"max iterations reached"`. Bash at `ralph.sh:890` emits `"max iterations reached ($TASKS_COMPLETED task(s) completed)"` — a templated string with the count interpolated. Python's bare label is a strict-port deviation in the summary text only (exit code matches bash now thanks to TASK-159). Cosmetic; flag if you want full bash-parity logs.
- **`skills/ralph-run/scripts/ralph/loop.py:319`** — `_update_after_iteration` calls `tasks_module.count_remaining()` **without** the whitelist argument, so when a `--tasks` whitelist is in play, the post-iteration `tasks_remaining` field reflects the **whole** To Do count, not the whitelisted count. Bash (`ralph.sh:347-367` + `count_remaining_tasks` callsite) honors the whitelist throughout. Pre-existing bug; the start-of-iteration write at loop.py:213 does pass `whitelist`, so the file flickers between correct (during run) and wrong (between runs). The summary uses the whitelist-aware value (loop.py:350) so it prints correctly. The bug is observable only by readers of `.ralph-status.json` between iterations.
- **Bash helpers still live alongside Python helpers** — expected, removal is TASK-156 AC #6.
- **3 parity test suites will go stale post-cutover** — TASK-156 AC #13 covers their deletion. Closed.

No hunks outside PRD/brainstorm scope were found in the deltas. The TASK-159/160/161 changes touch only:
- `skills/ralph-run/scripts/ralph/loop.py` (signal forwarding, max-iter exit, paused exit_reason)
- `skills/ralph-run/scripts/ralph/summary.py` (EXIT_REASONS extension)
- `skills/ralph-run/scripts/ralph/tools/__init__.py`, `tools/_subprocess.py`, `tools/claude.py`, `tools/opencode.py` (on_spawn hook)
- 3 new test files
- the 3 task files

All are traceable to the prior review's drift list.

---

## Reviewer Notes

- **All 3 acknowledged drifts from the 2026-06-22 review are now closed in code AND covered by new tests.** The TASK-160 implementation is particularly thoughtful: the RLock choice (signal handlers run synchronously on the main thread and can re-enter the locked region), the race-close in `set_active_subprocess` (covers the window between `Popen()` and the `on_spawn` callback), and the placement of `installer.raise_if_pending()` BEFORE the failed-iteration accounting (so a signal-killed iteration surfaces as `"interrupted"` rather than `"error"`) all show the implementer reasoning about adversarial interleavings. The 8 cases in `test_loop_signal_interrupt.py` exercise each of those design choices directly.
- **TASK-161 chose the cleaner option (a).** Extending `EXIT_REASONS` rather than splitting the summary emitter keeps the closed-set discipline intact and mirrors bash's flat `EXIT_REASON="paused"` variable directly. The cost is one PRD literalism deviation (PRD §3 US-005 AC #7 pinned a 4-string set), which is fine — the PRD itself under-specified vs. bash truth, and the prior review explicitly recommended this fix.
- **TASK-159 is a 2-line code change with 3 synthetic tests.** Bash parity confirmed at `ralph.sh:889-894`. No over-engineering.
- **Test count growth checks out.** Prior review: 178 tests. Current: 191. Delta = +13 = (+8 TASK-160 + +3 TASK-159 + +2 TASK-161). Matches the new test files exactly.
- **Latent pre-existing items I flagged above were NOT introduced by 159/160/161 and were missed by the prior review.** They're not blockers for TASK-156 cutover — the strict-port standard is bash behavior parity, and the `tasks_remaining` whitelist drift is a low-visibility, transient bug — but consider filing them as small follow-up tasks before TASK-156 starts the 5-clean-runs counter, OR add them to TASK-156's "pre-cutover hygiene" notes.
- **Strict-port discipline still well-respected.** Three follow-up tasks landed without any feature creep, schema additions, or new flags. The diffs are exactly as small as they need to be.

**Recommended next steps before TASK-156:**
1. Optional: file a small follow-up for the 3 latent items above (`"all specified tasks done"` collapse, `"max iterations reached (N task(s) completed)"` templated-text loss, `count_remaining()` missing whitelist arg at loop.py:319). All three are small, surgical fixes.
2. Then proceed with TASK-156 cutover, starting the 5-clean-runs counter.
