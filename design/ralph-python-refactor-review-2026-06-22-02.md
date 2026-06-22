# Feature Review: ralph-python-refactor (review #3)

**Date:** 2026-06-22
**Reviewer:** ralph-reviewer agent
**Diff range:** `1cd300b..HEAD` (14 Done tasks: 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 161, 162, 163, 164)
**Prior reviews:** `design/ralph-python-refactor-review-2026-06-22.md` (#1), `design/ralph-python-refactor-review-2026-06-22-01.md` (#2)
**Verdict: Partial**

**Passes run:** 1, 2, 3, 4, 5
**Passes skipped:** none — PRD and brainstorm both exist; PRD has Non-Goals, Success Metrics, and enumerated FRs.

Verdict remains **Partial** for the same structural reason as the prior two reviews: TASK-156 (cutover, US-007) is intentionally still To Do. All three pre-existing latent drifts surfaced in review #2 are now **Closed in code with tests**, and no new drift was introduced by TASK-162/163/164. With TASK-156 done, the verdict would flip to Aligned.

---

## Status of the three prior latent drifts (review #2 → review #3)

| Prior drift (review #2) | Task | Status now | Evidence |
|---|---|---|---|
| `loop.py:203` collapsed `"all specified tasks done"` (whitelist) and `"all tasks done"` (general) into one string | TASK-162 | **Closed** | `skills/ralph-run/scripts/ralph/summary.py:19-28` adds `"all specified tasks done"` to the closed set (now 6 strings); `skills/ralph-run/scripts/ralph/loop.py:203-205` branches on whitelist truthiness exactly as bash does at `ralph.sh:743` vs. `ralph.sh:751,881`; `tests/test_loop_whitelist_summary.py:60-88` pins both branches; summary substring guard at `test_loop_whitelist_summary.py:74` correctly prevents the longer label from false-passing the bare-label assertion. |
| `loop.py:288-289` lost bash's templated `"max iterations reached (N task(s) completed)"` | TASK-163 | **Closed** | `skills/ralph-run/scripts/ralph/summary.py:72-76` templates `(N task(s) completed)` into the rendered exit-reason line at the presentation boundary; `EXIT_REASONS` stays a flat closed set (`summary.py:19-28`), preserving the PRD §3 US-005 AC #7 design intent; `tests/test_loop_max_iter_summary.py:97-131` covers tasks_completed ∈ {0, 2}; literal `"task(s)"` (no pluralization) matches bash `ralph.sh:890`. Option (b) from the task description was chosen — cleaner than mutating the closed set. |
| `loop.py:319` `_update_after_iteration` called `count_remaining()` without the whitelist arg (real bug) | TASK-164 | **Closed** | `skills/ralph-run/scripts/ralph/loop.py:310-323` now takes a `whitelist: list[str] \| None` parameter and forwards it to `count_remaining(whitelist)` at `loop.py:322`; all 3 callsites (`loop.py:245`, `:261`, `:279`) pass `whitelist`; `tests/test_loop_whitelist_tasks_remaining.py:114-162` proves every JSON write reports the whitelisted count (load-bearing 99-vs-2 split — a regression that drops the whitelist would surface as a 99 landing in the captured `writes` list); non-whitelist regression test in same file. |

---

## Intent → Implementation Matrix (delta vs. review #2)

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| US-000 | sync nested-dir spike | Delivered | unchanged |
| US-001 | Scaffold + StatusFile | Delivered | unchanged |
| US-002 | Helpers ported | Delivered | unchanged |
| US-003 | Core internals | Delivered | unchanged |
| US-004 | claude subprocess + cleanup | Delivered | unchanged |
| US-005 | Opencode + entry point + E2E | Delivered | unchanged |
| US-006 | Strangler integration + R11 mirror | Delivered | unchanged |
| US-007 | Cutover + cleanup + downstream upgrade | Missing (by design) | TASK-156 still To Do; expected end state of this cycle. |
| FR-1 | Byte-identical status JSON | Delivered | unchanged |
| FR-2 | Exact CLI flag set | Delivered | unchanged |
| FR-3 | Atomic status writes | Delivered | unchanged |
| FR-4 | Heartbeat 5s + EXIT cleanup | Delivered | unchanged |
| FR-5 | Per-iter timeout, exit 124 = continue | Delivered | unchanged |
| FR-6 | SIGTERM kills whole process group + summary prints | Delivered | unchanged |
| FR-7 | Run summary, closed-set exit_reason | **Delivered (was Partial)** | Closed-set is now 6 strings including `"all specified tasks done"` (TASK-162); `"max iterations reached"` rendered with templated suffix (TASK-163). All bash exit-reason strings are now reachable via the Python port. |
| FR-8 | MODE: prefix verbatim | Delivered | unchanged |
| FR-9 | Sentinel parsing | Delivered | unchanged |
| FR-10 | Strangler dispatch | Delivered | unchanged |
| FR-11 | Devcontainer argv-as-list | Delivered | unchanged |
| FR-12 | RALPH_PROJECT_ROOT honored | Delivered | unchanged |
| FR-13 | Usage-cap exit-code contract | Delivered | unchanged |
| FR-14 | `--tasks` whitelist semantics | **Delivered (was Partial)** | TASK-164 closed the `_update_after_iteration` whitelist drop; between-iteration JSON now agrees with start-of-iteration JSON and the summary. All three write sites (loop.py:128, :215, :322, :353) consistently honor the whitelist. |
| FR-15 | pyright + ruff pass | Delivered | re-verified at HEAD: `uv run pyright skills/ralph-run/scripts` → 0 errors / 0 warnings; `uv run ruff check skills/ralph-run/scripts` → clean. |
| FR-16 | R11 mirror of two template files | Delivered | unchanged |

---

## Non-Goal Violations

None detected. All TASK-162/163/164 changes respected the non-goals:

- No schema additions to `.ralph-status.json` (TASK-164 only changes the *value* of an existing field).
- No new CLI flags (`ralph/args.py` unchanged in this delta).
- No new sentinels (`ralph/signals.py` unchanged).
- The closed-set grew from 5 → 6 strings (TASK-162), still bash-parity, still under-specified by PRD §3 US-005 AC #7. Same "bash parity beats PRD literalism" rationale used to justify TASK-161's `"paused"` addition in review #2.
- No `pyproject.toml [project]` table; no `uv.lock` checked in; no hook changes.

---

## Scope Cut Violations

None detected. Brainstorm §6 cuts still respected — TASK-162/163/164 are all bash-parity-closing follow-ups, not new feature work:

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
| `check_run_clean.py --run-only` exit 0 each run | Unmeasurable | Script absent; TASK-156 AC #1. |
| `check_run_clean.py --parity bash.json python.json` | Hypothesis only | TASK-156 AC #2. Schema parity already covered by golden-file round-trip. |
| pyright + ruff pass before every task-reviewer call | Measurable post-merge | Re-verified fresh at HEAD: 0 errors / 0 warnings. |
| All unit + 1 E2E test pass via `uv run pytest` | Measurable post-merge | **201 passed in 62.77s** on Python 3.14.4 at HEAD (was 191 at review #2; +10 = +2 TASK-162 + +6 TASK-163 + +2 TASK-164 — matches the new test counts the task notes record). |
| Zero behavior regressions per ralph-reviewer | Pending | This review. No regressions found. |
| ralph-sync directory propagation | Measurable post-merge | TASK-149 empirical pass. |

---

## Drift List

**No new drift introduced by TASK-162/163/164.** All three prior latent drifts from review #2 are now Closed (see table above).

The diffs are surgical and traceable to the prior review's flagged items:
- `skills/ralph-run/scripts/ralph/loop.py` — branch at :203, `_update_after_iteration` signature + callsites
- `skills/ralph-run/scripts/ralph/summary.py` — `EXIT_REASONS` extension, max-iter templated render
- `skills/ralph-run/tests/test_loop_whitelist_summary.py` (new)
- `skills/ralph-run/tests/test_loop_max_iter_summary.py` (new)
- `skills/ralph-run/tests/test_loop_whitelist_tasks_remaining.py` (new)
- `skills/ralph-run/tests/test_summary.py` (closed-set assertion updated 5→6)
- The 3 task files

No hunks outside PRD/brainstorm/backlog scope were found. The only outstanding strict-port deviations are the expected ones in TASK-156 territory (bash `ralph.sh` + 3 helper scripts + 3 parity test suites still present pending cutover).

---

## Reviewer Notes

- **All three latent drifts surfaced in review #2 are now closed with proportionate, surgical changes.** TASK-162 is a 1-line `if`-branch + 1-line set extension. TASK-163 is a 4-line render-time template. TASK-164 is a single signature change with 3 callsite updates. None of them touch concerns they weren't asked to touch.
- **TASK-163 chose Option (b) — the right call.** Keeping `EXIT_REASONS` as a flat closed set and templating the count at the presentation boundary preserves the design intent of PRD §3 US-005 AC #7 (exit reason as a classifier, separate from display state). The bash idiom interpolates because bash has no such separation. The docstring at `summary.py:64-71` correctly captures this rationale, including the bash-parity reason for the literal `"task(s)"` non-pluralization.
- **TASK-164's test design is load-bearing.** `_stub_count_remaining` returns 2 vs. 99 depending on whether the whitelist arg arrives — so the test proves *which branch* the loop took on every write, not just the final value. This is the kind of regression-trap the original bug needed: at the time the original code path was wrong, the summary was already correct (because it called `count_remaining(args.task_whitelist or None)` directly), so an end-of-run-only test would have false-passed. The spy on `StatusFile.write_atomic` captures every intermediate write.
- **Test count growth checks out.** Review #2: 191 tests. HEAD: 201 tests. Delta = +10 = (+2 TASK-162 + +6 TASK-163 + +2 TASK-164), matching the new test counts the task notes record. All green in 62.77s on Python 3.14.4.
- **Two minor things to note for TASK-156 (not blockers):**
  1. `loop.py:164-166` asserts `state.exit_reason in EXIT_REASONS` at end-of-run — this assertion now correctly passes for all 6 strings (verified by the new tests). Just confirming the invariant still holds post-extension.
  2. The summary docstring at `summary.py:1-11` mentions the closed-set is "6 strings" in spirit (it lists 6 by name) — accurate. Good documentation hygiene.
- **Strict-port discipline still tight.** Three follow-up tasks delivered without any feature creep, schema additions, or new flags. The diff stat for these three tasks is small (a handful of source lines + 3 test files).
- **Verdict rationale.** With these three landed, every non-cutover drift identified across two prior reviews is closed. The only remaining gap is TASK-156, which is the intentional end-state of the refactor. The next review should be the cutover-completion review (verdict-flip candidate to Aligned).

**Recommended next step:** Proceed with TASK-156 cutover. Start the 5-clean-runs counter. The Python orchestrator is now bash-parity-complete to the extent the prior two review cycles could verify.
