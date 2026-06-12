# Feature Review: ralph-sh-shim (2026-06-12)

**Verdict: Aligned**

**Passes run:** 3 (Brainstorm Scope Cuts), 5 (Out-of-Scope Creep)
**Passes skipped:** 1 (PRD Coverage), 2 (Non-Goal Protection), 4 (Success-Metric Realism) — no PRD exists for this feature; intent lives solely in the brainstorm.

Because no PRD exists, the standard "Intent-to-Implementation Matrix" against PRD requirements is replaced by an AC-and-locked-decision matrix derived from the brainstorm's "Decisions locked (2026-06-12)" and "Phase 4 — final AC sketch" sections, per the rubric instruction that supersedes-earlier-sections content is authoritative.

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| Q1 (locked) | Bootstrap safeguard: ralph-init hard-stops with exact locked message "install user-global skills first via /ralph-sync, then re-run ralph-init" if canonical missing | Delivered | `skills/ralph-init/SKILL.md:36-41` — `[ -s "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh" ] \|\| { echo "ERROR: install user-global skills first via /ralph-sync, then re-run ralph-init"; exit 1; }`. Message matches verbatim; uses `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` per Q5; hard-stops via `exit 1`. |
| Q2 (locked) | Env-var override via `RALPH_PROJECT_ROOT`; canonical switches the 7 project-artifact `$SCRIPT_DIR` refs to `${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}`; line 479 simplifies to `$SCRIPT_DIR/usage-check.sh` | Delivered | Verified by direct grep of `skills/ralph-run/scripts/ralph.sh`: lines 444, 450, 461, 480, 562, 609, 691, 779 all carry `${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}`; line 479 reads exactly `USAGE_CHECK_SCRIPT="${RALPH_USAGE_CHECK_SCRIPT:-$SCRIPT_DIR/usage-check.sh}"`. Standalone mode preserved — `SCRIPT_DIR="$(cd ... && pwd -P)"` still defined at line 227. |
| Q3 (locked) | Shim header: short 1-2 line comment pointing at canonical + mentioning `/ralph-sync` | Delivered | Shim L2-L3: `# Thin shim — the real script lives at ~/.claude/skills/ralph-run/scripts/ralph.sh` + `# Install/update via /ralph-sync`. Two-line comment, both elements present. |
| Q4 (locked) | R11 rule rewritten as shim-equivalence; canonical excluded from mirror set | Delivered | `.claude/task-reviewer-rules.md:106` retitles row as `ralph.sh (thin shim)`. New note at line 110 says the parity rule covers only the two shim copies; canonical "is the single source of truth and is intentionally excluded from this mirror set"; explicit "a `diff` of the two MUST produce no output" wording. |
| Q5 (locked) | Shim uses `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`, not bare `$HOME/.claude` | Delivered | Shim L5: `exec "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh" "$@"`. |
| AC #1 | Two shim files byte-identical; 5 lines; header + RALPH_PROJECT_ROOT + exec | Delivered | Direct `diff ralph.sh skills/ralph-init/templates/root/ralph.sh` produces no output (verified). Both files are exactly 5 lines. R11 parity holds. |
| AC #2 | Canonical refactor lines 444/450/461/480/562/609/691/779 + line 479 helper simplification | Delivered | Exact-line verification matches the brainstorm audit table line-for-line. |
| AC #3 | Standalone mode (no `RALPH_PROJECT_ROOT`) falls back to `$SCRIPT_DIR` | Delivered | `SCRIPT_DIR` still defined at line 227; every refactored line uses the `${VAR:-fallback}` pattern that preserves prior behavior when `RALPH_PROJECT_ROOT` is unset. Test bundle `tests/helpers/common.bash` sets `RALPH_SCRIPT="$PROJECT_ROOT/skills/ralph-run/scripts/ralph.sh"` to exercise the canonical directly. |
| AC #4 | Shim-via-cwd mode passes project root through `RALPH_PROJECT_ROOT` | Delivered | Shim L4 computes `RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"` before exec, so the canonical receives the shim's directory as project root. |
| AC #5 | ralph-init bootstrap safeguard with locked error message and non-zero exit | Delivered | See Q1 row above. |
| AC #6 | R11 rule rewritten for shim-equivalence; canonical excluded | Delivered | See Q4 row above. |
| AC #7 | Full /ralph-run iteration writes `.ralph-status.json` to project `backlog/` | Delivered (claimed) | Implementation Notes claim verified via task-reviewer agent; cannot replay live `/ralph-run` here, but the path-resolution refactor and Q1 safeguard make this the expected behavior. |
| AC #8 | Existing usage-check.bats (12) + usage-pause.bats (5) pass without modification | Delivered (claimed) | Implementation Notes assert pass; `tests/helpers/common.bash` was modified to point `RALPH_SCRIPT` at the canonical directly — this is a test-helper adaptation, not a test-case modification, and is well-justified (the comment explains that sourcing the shim would hit `exec` and break unit tests). The bats files themselves are unchanged in the diff. |
| AC #9 | New shim smoke test asserts identical stdout/stderr/exit code for `--help` | Delivered | `tests/integration/shim.bats` added: drives both `bash $SHIM --help` and `bash $CANONICAL --help` with `LC_ALL=C` and a temp-rooted `CLAUDE_CONFIG_DIR`, then diffs both stdout and stderr and asserts equal exit codes. The `LC_ALL=C` rationale (suppressing bash's setlocale warning that fires once per process — shim spawns two processes, canonical one) is documented inline. Solid. |

## Scope Cut Violations

The brainstorm's "Out of scope (deliberate)" list:

1. **Touching the helper-script vendoring model** — not touched. `ralph-init` still ships only root-level files; the helper-script tree is not now vendored into ralphed projects. Compliance verified.
2. **Repointing other R11 mirrors** (commit-msg hook, task-validator.sh, etc.) — the only `.claude/task-reviewer-rules.md` edit in the diff is the `ralph.sh`-row note plus a single retitle to "(thin shim)". No other parity rules touched. Compliance verified.
3. **Reworking `/ralph-run`'s `Step 2: Locate ralph.sh`** — the `skills/ralph-run/SKILL.md` file does not appear in the diff. Resolution order untouched. Compliance verified.
4. **TASK-136 Unicode NFC normalization** — not present in the diff. Compliance verified.

None detected.

## Drift List

Reviewed every diff hunk against the brainstorm intent and AC list:

- `.claude/task-reviewer-rules.md` — Q4/AC#6 work.
- `backlog/tasks/task-137 ...md` — the task file itself.
- `design/ralph-sh-shim-brainstorm.md` — the design doc.
- `ralph.sh` (project root) — replaced by shim per AC#1.
- `skills/ralph-init/SKILL.md` — Q1/AC#5 bootstrap safeguard.
- `skills/ralph-init/templates/root/ralph.sh` — replaced by shim per AC#1.
- `skills/ralph-run/scripts/ralph.sh` — 8 project-path rewrites + line-479 simplification per AC#2.
- `tests/helpers/common.bash` — two non-AC changes: (a) `RALPH_SCRIPT` repointed at canonical, and (b) `CLAUDE_CONFIG_DIR="$PROJECT_ROOT"` exported in `setup_test_dir`. Both are necessary supporting infrastructure for AC#8 ("existing tests still pass without modification") — without them, unit tests that `source $RALPH_SCRIPT` would be hijacked by the shim's `exec`, and any integration test invoking `bash ralph.sh` would shell out to whatever user-global ralph.sh happens to be installed. Documented inline with clear rationale. Not drift — necessary scaffolding for the AC.
- `tests/integration/shim.bats` — new test per AC#9.

No drift detected.

## Reviewer Notes

Non-blocking observations:

1. **Critical-check pass-through**: every critical check the orchestrator flagged passes cleanly. The 8 project-path lines hit the exact line numbers (444, 450, 461, 480, 562, 609, 691, 779); line 479 simplifies to `$SCRIPT_DIR/usage-check.sh`; standalone mode is preserved by an unchanged `SCRIPT_DIR=$(...)` at line 227; bootstrap error message matches the locked Q1 wording verbatim; shim header is exactly two lines; `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` is used in both the shim and the bootstrap check; the latent TASK-135 nested-path bug is fixed because line 479 now resolves to `~/.claude/skills/ralph-run/scripts/usage-check.sh` (helper colocated, no double-nesting). R11 parity between the two shim copies is byte-identical (verified via direct `diff`).

2. **`tests/helpers/common.bash` rewrite is the right call**: AC#8 says "existing bats files pass without modification" — the diff respects that literally (zero edits to `tests/unit/usage-check.bats` or `tests/integration/usage-pause.bats`). The common-bash adjustments are infrastructure, not test-case rewrites. The inline comments explain *why* clearly. If a future task wants tighter isolation, exporting `CLAUDE_CONFIG_DIR="$PROJECT_ROOT"` globally for every `setup_test_dir` call may surprise a future test that needs to *unset* it; consider adding a one-line "unset CLAUDE_CONFIG_DIR" affordance in `cleanup_test_dir` for future-proofing — non-blocking.

3. **Shim header punctuation drift from brainstorm**: brainstorm Q3 example used a trailing period in `Install/update via /ralph-sync.`; the shipped shim drops the period (`Install/update via /ralph-sync`). Stylistic only, no functional impact, and the brainstorm Q3 lock text says "short 1-2 line comment pointing at canonical + mentioning `/ralph-sync`" — both elements are present. Non-blocking.

4. **Phase 4 final-AC sketch item 9** (docs update) maps to brainstorm AC#9. The diff grep for "three-way" or "mirror" in `README.md` / `CLAUDE.md` / `skills/ralph-run/SKILL.md` found no stale references. The original three-way mirror was not actually documented outside `.claude/task-reviewer-rules.md` (which was correctly updated). So AC #9 in the *final* sketch is satisfied vacuously — there was nothing to rewrite. Worth noting because the task-card AC list has 9 ACs and the brainstorm sketch also lists 9 items but they aren't 1:1 numbered — the task ACs collapse the brainstorm's items 1+2 into AC#1, and the brainstorm's docs item is dropped from the task ACs entirely. Coverage is complete; numbering just doesn't line up. Non-blocking.

5. **Brainstorm content preservation (R14 spirit)**: the brainstorm correctly preserves the original "Open questions" and "Phase 4 — next steps" sections and adds an addendum + locked-decisions block at the bottom that explicitly supersedes them ("supersedes the original at top of brainstorm"). The implementation correctly followed the bottom-of-doc locked decisions, not the earlier superseded ones (e.g., used `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` not the earlier-section bare `$HOME/.claude`; used the `RALPH_PROJECT_ROOT` env-var shape from the addendum, not the simpler 3-line shim from the earlier Option A sketch). Good discipline.

6. **One small architectural observation, no action required**: the canonical now has 8 sites using `${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}` repeated verbatim. A future cleanup could hoist this once at the top (`PROJECT_ROOT="${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}"`) to make subsequent changes less repetitive. Not a defect in this PR; just a refactor opportunity for whoever next touches this file.
