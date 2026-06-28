# Feature Review: ralph-python-refactor (final cutover — TASK-156, with TASK-175/176 in-window)

Date: 2026-06-28

**Verdict: Aligned**

**Passes run:** 1, 2, 3, 4, 5
**Passes skipped:** none — both PRD (`design/ralph-python-refactor-prd.md`) and brainstorm (`design/ralph-python-refactor-brainstorm.md`) are present, both carry Non-Goals and Success Metrics sections.

Scope note: this is the *final cutover* delta. The port itself (US-001..US-006 / TASK-149..164) is established Aligned in the 2026-06-22 cumulative reviews, and the TASK-175/176 gap fixes are established Aligned in the 2026-06-24 delta review. This review focuses on US-007 cutover discipline and spot-checks 175/176 rather than re-litigating them. No custom rules file (`.claude/ralph-review-rules.md`) present; standard rubric only.

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| US-007 AC#1 | `check_run_clean.py --run-only` codifies the 6-check gate | Delivered | `tests/scripts/check_run_clean.py` (+163), stdlib-only PEP 723. Brainstorm Q1/§Locked 6-check definition matches. |
| US-007 AC#2 | `check_run_clean.py --parity` schema parity | Delivered | Same file; `--parity` smoke recorded in notes (21-field parity PASS). |
| US-007 AC#3 | 5 consecutive `RALPH_IMPL=python` runs (bash still default) pass `--run-only`, documented | Delivered | Phase B notes: runs 1–5 (TASK-165..169), 4 full 6-check PASS + run 1 manually verified (host-branch artifact, diagnosed as bash-parity, not regression). |
| US-007 AC#4 | Default flipped to python in live `ralph.sh`, SKILL.md, template `ralph.sh` (R11 preserved) | Delivered | Phase C commit `531f130`; flip applied to all 3 mirror sites. |
| US-007 AC#5 | 5 MORE consecutive clean runs, python default | Delivered | Phase D notes: runs 6–10 (TASK-170..174), all 6-check PASS, no `RALPH_IMPL=` env var (implicit default confirmed). |
| US-007 AC#6 | Delete inner bash: `ralph.sh`, `preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh` | Delivered | Diff: `ralph.sh` (−895), `preflight.sh` (−162), `wait-heartbeat.sh` (−25), `usage-check.sh` (−101) all removed. Plus 2 orphan bash harnesses + 3 parity suites. |
| US-007 AC#7 | Outer shim back to ~6 lines, Python-only (live + template) | Delivered | `ralph.sh` is 7 lines, execs `uv run …/ralph_orchestrator.py`; live vs template `diff` → IDENTICAL. `RALPH_IMPL` dispatch removed. |
| US-007 AC#8 | `/ralph-run` skill `impl=` removed | Delivered | SKILL.md row dropped; `grep impl=` → NONE. `RALPH_IMPL` export removed from launch block. |
| US-007 AC#9 | CLAUDE.md Language line tightened | Delivered | "Python (orchestrator) + Bash (hooks, git hooks, sync, firewall) + Markdown (skills, agents, docs)" — verbatim match. |
| US-007 AC#10 | Downstream upgrade instructions in notes | Delivered | Notes carry path (A) `ralph-init upgrade` and path (B) hand-patch 7-line shim + `Bash(uv run:*)` rule, with uv/Python 3.14 prereq. |
| FR-10 | Strangler dispatch honors `RALPH_IMPL`; default flips to python at cutover | Delivered (terminal state) | Post-cutover `RALPH_IMPL` is no longer honored — the env-var dispatch is intentionally retired per AC#7; this is the documented end-state, not a regression. |
| FR-15 | pyright + ruff pass | Delivered | task-reviewer recorded pyright 0 errors, ruff clean (also stated as pre-verified at merge). |
| FR-16 | R11 template mirror updated in same task | Delivered | Template `ralph.sh` + `settings.local.json` template updated alongside live; R11 note in `.claude/task-reviewer-rules.md` repointed to `ralph_orchestrator.py`. |

PRD §6 final shim shape note: the §6 sketch still shows the strangler dispatch form; the landed 7-line Python-only shim is the AC#7 cutover end-state and supersedes that sketch. Not a deviation — the §6 block documents the dual-running shape, AC#7 documents the post-cutover shape.

## Non-Goal Violations

None detected. Cross-checked PRD §5 against the cutover diff:
- No status-JSON schema change — `StatusFile` untouched in this delta.
- No new/renamed CLI flags — no argparse touched.
- No new sentinels, no retry-policy change, no worktree/reviewer/notifications/`--plan`.
- No hook, git-hook, `sync.sh`, `utc-to-moscow.sh`, or `init-firewall.sh` changes.
- No `[project]` section / no `uv.lock` / no logging migration / no Python version bump.
- The one pre-disclosed strict-port deviation (Python `devcontainer up` aborts on non-zero exit where bash continued) remains the **only** behavior delta, sanctioned by TASK-175 AC#4 and pre-disclosed in the 2026-06-24 review. The final-cutover diff introduces no new deviation.

## Scope Cut Violations

None detected. The brainstorm Stage 4 migration plan — *5 clean runs → flip default → 5 more clean runs → delete bash, simplify shim to 6 lines* — matches what landed phase-for-phase (Phases B→C→D→E). Cutover discipline was followed in order: gate harness built first (Phase A), 5+5 runs documented with elapsed/exit_code/tasks_done snapshots, deletion only after the 10th clean run. No brainstorm-cut feature (richer sentinels, retry classification, external reviewer) leaked in.

## Drift List

No drift in TASK-156's own diff. Every hunk traces to an AC. One pre-existing stale-reference observation (informational, not introduced by this diff):

- `skills/ralph-init/SKILL.md` (untouched by this cutover — `git diff --stat` shows no change) still invokes `preflight.sh` / `wait-heartbeat.sh` as `bash …` and writes `Bash(... preflight.sh:*)` / `wait-heartbeat.sh:*` permission rules (lines 203, 210–222, 291–297, 552). These point at scripts this cutover deleted. TASK-156's own notes flagged this exact item as a known Phase E follow-up ("orphan rules in existing settings.local.json are harmless deadweight"; ralph-init narrow-rule merge to be cleaned separately). It is harmless at runtime — the live `ralph-run/SKILL.md` was correctly repointed to `python -m ralph.preflight|wait_heartbeat`, and the permission check is at the Bash-tool layer, so stale allow-rules are inert. But it is a real loose end: a fresh `ralph-init` bootstrap or upgrade will still seed dead permission rules and the SKILL.md narrative still describes the deleted bash helpers. Recommend a one-line follow-up task to repoint `ralph-init/SKILL.md` to the Python entrypoints and drop the two `.sh` narrow rules. This is the only cutover-completeness gap; it does not lower the verdict because it is out of TASK-156's AC scope, self-disclosed, and runtime-inert.

## Success Metric Assessment

| Metric | Status | Notes |
|--------|--------|-------|
| 5 consecutive clean Python runs (pre-flip gate) | Measurable — exercised | Phase B runs 1–5 documented; `check_run_clean.py --run-only` PASS recorded per run. |
| 5 more clean runs (post-flip burn-in) | Measurable — exercised | Phase D runs 6–10 documented; all 6-check PASS, python implicit default. |
| `check_run_clean.py --run-only` exit 0 on each of 10 gating runs | Measurable — exercised | 9/10 full 6-check PASS in notes; run 1 manually verified clean (branch-context artifact diagnosed, not a gate failure). |
| `--parity` schema parity passes | Measurable — exercised | Phase A `--parity` smoke PASS (21 fields). |
| pyright + ruff pass before task-reviewer | Measurable | Recorded green at merge (pyright 0, ruff clean). |
| All unit tests + E2E pass | Measurable | pytest 185 passed at merge (parity suites removed; net per `--stat`). |
| Zero behavior regressions caught by ralph-reviewer (final gate) | Measurable — this review | Aligned; only the pre-disclosed devcontainer-up deviation, no new regression. |

## Reviewer Notes

- **Cutover discipline is exemplary.** The strangler-fig plan was executed in the exact brainstorm-specified order with mechanical evidence at each gate. The decision to use 10 throwaway `cutover-smoke`-labelled victim tasks (TASK-165..174, deliberately *not* `feature:`-labelled so they don't pollute future reviews) is a thoughtful test-hygiene choice that still exercised the full task-pick → MODE → claude → diff → status path.
- **Shim parity is verified byte-for-byte** (live vs template `diff` produced no output), satisfying R11 in its post-cutover form. The R11 note itself was correctly repointed from the deleted canonical `ralph.sh` to `ralph_orchestrator.py`.
- **No orphan references to the deleted bash scripts** exist in any tracked file outside (a) the design docs and old task files (historical, expected) and (b) `ralph-init/SKILL.md` (the one loose end above). `git grep` across the tree for `RALPH_IMPL` / `impl=` / `scripts/*.sh` is clean.
- **Spot-check of 175/176 in-window changes** confirms they are exactly the commits already reviewed Aligned on 2026-06-24 (run-log tee, devcontainer.py `up`). No re-litigation needed; they did not disturb the cutover.
- **Single recommended follow-up:** file a one-line task to repoint `skills/ralph-init/SKILL.md` (and its templated narrow-rule merge) from `preflight.sh`/`wait-heartbeat.sh` to the `python -m ralph.preflight|wait_heartbeat` entrypoints, so downstream bootstraps/upgrades stop seeding dead permission rules. This closes the last cosmetic seam of the cutover; it is non-blocking and the refactor is otherwise at steady state.
