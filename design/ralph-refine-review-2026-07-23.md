# Feature Review: ralph-refine

**Verdict: Aligned**

**Date:** 2026-07-23
**Reviewer:** ralph-reviewer agent (cumulative cross-task review)
**In-scope tasks:** TASK-201..209 (US-001..009)
**Diff range:** `138cf91`..HEAD

**Passes run:** 1 (PRD Coverage), 2 (Non-Goal Protection), 3 (Brainstorm Scope Cuts), 4 (Success-Metric Realism), 5 (Out-of-Scope Creep)
**Passes skipped:** none — both `design/ralph-refine-prd.md` and `design/ralph-refine-brainstorm.md` are present, and the PRD carries Non-Goals, Success Metrics, and a Technical Considerations/cross-task-invariants section.

No custom rules file (`.claude/ralph-review-rules.md`) was found; the standard rubric plus the four mandated cross-task invariants were applied.

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| US-001 | `ralph/refine/` scaffold + `refine_orchestrator.py` entrypoint | Delivered | Package present (`__init__,args,cli,extract,roles,loop,summary`); `./refine.sh --help` resolves via tier-2 and prints usage, exit 0; pyright strict 0 errors |
| US-002 | CLI arg parsing + validation, defaults match refine.sh | Delivered | `args.py` (`RefineArgs` frozen dataclass); SKILL.md flag table matches PRD defaults (`type=md, tool=claude, model=claude-opus-4-8, effort=medium, timeout=15, max-iter=10, threshold=8, on-error=stop, retry-count=2`); `test_refine_args.py` (29 cases) |
| US-003 | artifact/summary/score extraction from tee | Delivered | `extract.py`: non-greedy DOTALL tag regex (single-line TASK-10, out-of-block noise AC#7), `_strip_leading_blank_lines` (TASK-12), `ExtractionError` carries transcript (TASK-16), reads `ToolResult.stdout_path`; `test_refine_extract.py` (36 cases) |
| US-004 | Author/reviewer prompt composition | Delivered | `roles.py` pure builders; exported `ARTIFACT_INSTRUCTION`/`REVIEW_INSTRUCTION` constants pin the shared tag contract; `test_refine_roles.py` (23 cases) covering all 5 paths + guards |
| US-005 | Refinement loop, output structure, summary | Delivered | `loop.py` + `summary.py`; per-iteration `artifact-vN`/`review-vN`, threshold exit 0 / max-iter exit 1, `--on-error`/`--retry-count`/`--resume`/`--dry-run`/`--verbose`, SIGTERM via reused `on_spawn`; `test_refine_loop.py` (26 cases) |
| US-006 | Root `refine.sh` shim + R11 parity + init seeding | Delivered | `diff refine.sh templates/root/refine.sh` → IDENTICAL; R11 table row present (line 106) with explicit shim note; ralph-init SKILL.md seeds it; `--help` works via tier-2 |
| US-007 | 3 example role sets ported verbatim | Delivered | 9 files under `examples/{article,drawio,plantuml}/`; all authors carry `<artifact>`, all reviewers carry `SCORE: N` + `<summary>`; extracted byte-for-byte from task blocks |
| US-008 | `ralph-refine` SKILL.md + single-approval flow | Delivered | `SKILL.md` present, discoverable frontmatter, single sandbox-bypass launch in Step 3, references bundled examples, no plugin.json edit |
| US-009 | e2e fake-claude + green toolchain | Delivered | `test_refine_e2e.py` drives real orchestrator out-of-process with a fake `claude` speaking the protocol; `uv run pytest` = 317 passed, `ruff` clean, pyright strict 0 errors |
| FR-1 | Package under the single pinned Python root, imports `ralph.*` | Delivered | Lives under `ralph-run/scripts/ralph/refine/`; imports `ralph.tools`/`devcontainer` directly |
| FR-2 | LLM I/O only through `ralph.tools`, no bespoke subprocess | Delivered | `tool.run(...)` at loop.py:344 is the sole invocation path; only `subprocess` token in the package is the `Popen[bytes]` type annotation on the reused `on_spawn` callback |
| FR-3 | Tag protocol resilient to combined stdout+stderr noise | Delivered | `extract.py` keys on non-greedy tags + line-anchored `^SCORE:`, reads `stdout_path` tee, `errors="replace"` |
| FR-4 | Terminate score≥threshold (0) / max-iter (1), always write final+summary | Delivered | `_run_loop` / `_finalize` / `_finalize_max_iter`; e2e asserts both branches |
| FR-5 | CLI parity with refine.sh | Delivered | Full flag set + defaults verified |
| FR-6 | 5-tier resolver, R11-paired, init-seeded | Delivered | byte-identical diff + R11 row + seeding |
| FR-7 | Separately-invocable skill, no backlog/tasks.py coupling | Delivered | `_SignalForwarder` kept in-package specifically to avoid importing `ralph.loop`/`tasks`; no `backlog` import in the package |
| FR-8 | Single-approval invocation | Delivered | Exactly one `dangerouslyDisableSandbox` launch; locate/read steps sandbox-safe; no helper shim requiring a seeded rule |

## Cross-task invariants — all four hold

1. **Tool-layer reuse** — verified: sole LLM path is `tool.run`; extractor reads `ToolResult.stdout_path`; no bespoke subprocess/timeout code.
2. **Tag protocol** — verified consistent across `roles.py` (exported instruction constants), `extract.py`, all 3 example reviewer/author sets, and the e2e fixture (`fake_refine_claude.py` imports the real `REVIEW_INSTRUCTION` to distinguish roles).
3. **R11 template parity** — verified: `diff` produces no output; R11 table updated.
4. **Single-approval launch** — verified: one sandbox-bypass prompt; no second prompt path.

## Non-Goal Violations

None detected. The PRD non-goals (detached/watch phase-2, common-package extraction, retiring `~/dev/ai/refine`, backlog integration, separate-streams tool variant, new artifact types) are all respected: no `.refine-status.json`/heartbeat/watch skill was added, `ralph.tools`/`devcontainer`/`signals` stay in place unchanged, the loop is backlog-independent, the combined-stdout tee is accepted, and only `md|drawio|puml` are supported.

## Scope Cut Violations

None detected. Brainstorm-declared cuts hold: no literal bash port, `ralph.loop` is not reused (refine has its own smaller loop + self-contained `_SignalForwarder`), phase-2 detach is absent, and common-package extraction was not attempted.

## Success Metric Assessment

| Metric | Status | Notes |
|--------|--------|-------|
| `./refine.sh` converges and writes `iterations/final.md` (parity with `make demo`) | Measurable post-merge | `test_refine_e2e.py` proves convergence + `final.{type}` + `summary.md` + exit 0 against a real out-of-process orchestrator |
| `uv run pytest` count increases; all green | Measurable post-merge | 317 passed (grew across tasks: 204→233→269→292→314→317); confirmed green now |
| Zero changes to `ralph.tools`/`devcontainer`/`signals` source | Measurable post-merge | No package changes to the reused layer; only the `on_spawn` contract is consumed |
| `ralph-refine` appears as an invocable skill after reload | Hypothesis only | SKILL.md exists with discoverable frontmatter and no plugin.json edit needed (skills auto-discover); actual loader listing not asserted by an automated test — acceptable, noted in the task as manually verified |

## Drift List

No drift detected. Every diff hunk in TASK-201..209 traces to a US/FR or a stated invariant (package modules, tests, `refine.sh` + template, R11 table row, ralph-init seeding, SKILL.md, example roles). The out-of-scope TASK-210 `ralph-stop/SKILL.md` graceful-drain delta that rides along in linear history was excluded from this review and is not attributable to ralph-refine.

## Reviewer Notes

- The implementation is unusually clean against intent — all 9 stories, all 8 FRs, and all 4 cross-task invariants verified on disk (not merely from the diff): `diff` parity is byte-identical, `ruff`/`pyright strict`/`pytest` are all green, and the sole `subprocess` token in the package is a type annotation on the reused `on_spawn` callback.
- One nuance worth recording (already adjudicated correctly in TASK-207): PRD US-007 AC#2 parenthetically says the drawio *reviewer* references the `arch-draw` skill, but the verbatim source places that reference in drawio `author.md` only. The implementer preserved verbatim fidelity (AC#5) over the parenthetical hint. This is the right call — verbatim-match was the primary instruction — but if design intent truly wanted the reviewer to load `arch-draw`, that is a source-content fix to make upstream, not an implementation defect.
- Minor housekeeping (non-blocking): committed `__pycache__/*.pyc` files exist under `ralph/refine/` in the working tree (including stale `cpython-311` artifacts). These are build artifacts; confirm `.gitignore` excludes them so they are not tracked. This does not affect the verdict.
- No action required to reach Aligned. Recommend proceeding to merge and filing the deferred follow-ups (phase-2 detach, common-package extraction, `~/dev/ai/refine` retirement) as separate work per the brainstorm.
