# Brainstorm-to-task hand-off: distill, don't reference

## Context / trigger

Across the recent `ralph-init-hook-ordering` feature, the Phase 4 hand-off pattern was: task description includes a line like `Design conclusions: design/<name>-brainstorm.md (Options A–E walked, Q1–Q5 locked, addendum 2026-06-13)`. Then **two** independent consumers read that same brainstorm file:

1. **Autonomous Ralph**, when implementing the task — reads the full brainstorm for context.
2. **ralph-reviewer**, when judging alignment — reads the same brainstorm as intent source.

Three failure modes follow:

1. **Token cost.** Brainstorms grow during the walk: 5 options enumerated, 5 questions with tradeoffs, an addendum that supersedes earlier sections. The 2026-06-13 brainstorm was 170 lines / ~10K tokens. Ralph reads all of it on every iteration.
2. **Evolution mismatch.** The doc-start sections explore options that the doc-end addendum rejects (e.g., Option D rejected in Q5; original Step 3.7a description superseded by the locked split). An LLM weighting the surface area can be misled by superseded reasoning.
3. **Review independence collapses.** When Ralph implements from the brainstorm and the reviewer judges from the brainstorm, "review" degenerates to "Ralph copied the doc faithfully." No real second-opinion check. The whole point of ralph-review is independent judgment, and that's only possible when the contract (what Ralph sees) and the intent (what reviewer sees) are different artifacts.

## Direction (locked)

**Option A — Distill.** Phase 4 hand-off does NOT reference the brainstorm file. It copies the locked decisions + rationale + AC list **verbatim into the task description**. The brainstorm doc becomes a pure human-facing design archive — never read by Ralph, never the source of truth for ralph-review.

Why A wins over B (Promote to PRD) and C (Section markers):

- **vs B (PRD layer for everything):** PRD generation is heavy for ad-hoc work where most ralph-task invocations don't justify the formality. A keeps the lightweight `ralph-task` flow intact. B becomes the right tool for multi-task features that explicitly need an intent layer for ralph-review independence — but it's opt-in, not default.
- **vs C (Section markers):** Doesn't actually fix the review-independence problem; both consumers still pull from the same doc. And tag discipline degrades over time as new authors forget the convention.

A also has the nicest invariant: **the brainstorm is for humans; the task is for the implementer.** Whoever they are — human or AI — they read exactly one of the two.

## What flows where (sketched)

```
brainstorm.md  ──────────────► [human author, design exploration]
     │                          [ralph-reviewer if no PRD exists]
     │ distill (Phase 4 hand-off)
     ▼
task description (-d) + ACs ──► [implementer: human, autonomous Ralph]
     │                          
     │ implement
     ▼
code changes ─────────────────► [ralph-reviewer judges against brainstorm/PRD]
```

In the distilled-task world: ralph-reviewer still reads the brainstorm (or PRD) as **intent**; Ralph reads only the task as **contract**; independence is preserved because the two artifacts are different.

## Open questions

1. **What exactly gets distilled?** Minimum viable distillation = AC list (already in task). Maximum = locked decisions + rationale + scope cuts + AC list verbatim in task `-d`. Where's the right line? Proposal: locked decisions (Q-lock summaries) + per-decision rationale (1 sentence each) + AC list. Skip the option-walk reasoning (Option A vs B vs C). Skip rejected options. Keep scope cuts (they prevent regression).

2. **Where does the discipline live?** Two surfaces could enforce it:
   - **brainstorm-rules.md "Save Design Conclusions"** — add a "Distillation" subsection: when saving the Phase 3 addendum, also write a "Distilled for ralph-task" block that the Phase 4 hand-off uses verbatim.
   - **ralph-task skill** — add a MUST rule: task descriptions never contain a path-like reference to a brainstorm file. Self-check after create greps for `design/.*brainstorm.md` in the task body and warns if found.
   - **Both** — brainstorm-rules writes the distillation block; ralph-task pulls from it. Belt and suspenders.

3. **How does ralph-review change?** Three options:
   - Status quo: reviewer reads brainstorm as intent; task is contract; independence achieved automatically because they're different.
   - Soft addition: reviewer warns if it finds a brainstorm-file reference in the task body (signal that distillation didn't happen).
   - Hard addition: reviewer refuses to run if the in-scope tasks reference brainstorm files in their `-d`.
   I lean status-quo plus the soft warning — refusing creates friction without much added safety.

4. **When does the PRD layer get pulled in (Option B fallback)?** Heuristics:
   - Single-task feature: never need a PRD. Distillation suffices.
   - Multi-task feature (e.g., the current `ralph-init-hook-ordering` with TASK-139 + TASK-140): each task distills its own scope; if there are cross-task invariants the brainstorm captures, those go into a PRD as the shared spec. ralph-review then reads the PRD.
   - Worth coding the threshold? Or leave it to author judgment with brainstorm-rules pointing to "generate a PRD if cross-task spec needed"?

5. **Migration of existing tasks.** Two tasks just merged (TASK-139, TASK-140) reference `design/ralph-init-hook-ordering-brainstorm.md` in their descriptions. Options:
   - Leave alone — Done tasks are historical artifacts; the convention starts with the next task.
   - Rewrite in place — backfill distillation. Heavy lift, low value.
   - Add a one-line note in those tasks: "Filed under pre-distillation convention." Minimal.
   I lean (a) leave alone. The new convention applies forward.

6. **What about edge cases — large content the implementer truly needs?** If a task needs a verbatim 30-line code snippet or a 5x5 decision matrix to reproduce a result, that's already inline per ralph-task's "description may include code blocks" rule. The distillation rule doesn't reduce that; it just forbids `see file X` for design rationale.

7. **README + skill doc surface area.** Files that describe the brainstorm → task pipeline today and need to align with the new rule:
   - `README.md` — has a section on Ralph workflow? (Check.)
   - `~/.claude/skills/ralph-task/SKILL.md` — canonical pattern, MUST rules.
   - `~/.claude/skills/ralph-review/SKILL.md` — intent-doc resolution.
   - `~/.claude/skills/ralph-prd/SKILL.md` — when to invoke (PRD-shaped vs ad-hoc).
   - `.claude/brainstorm-rules.md` — Save Design Conclusions (Case A/B), Phase 4 Override.
   - User-global `~/.claude/skills/ralph-task/` mirrored copy.
   Project-local lives in `.claude/`; user-global is propagated via ralph-sync.

## Scope cuts (preliminary — confirm before locking)

- **Replacing brainstorm-rules.md wholesale.** No — only Save Design Conclusions + Phase 4 Override change.
- **Forcing PRD generation for every feature.** No — that's Option B, rejected as the default. Optional for multi-task / cross-task-invariant features.
- **Auto-rewriting existing Done tasks.** No — historical artifacts stay as-is.
- **Tooling change: extraction script that pulls "distilled" sections out of brainstorm files.** No — manual discipline is enough; tooling adds complexity for a low-volume process.
- **Changes to ralph-prd flow.** Minimal — clarify "when needed" guidance; don't restructure the skill.
- **Adding new "design/<name>-spec.md" or "decisions.md" file kind.** No — distillation lives in the task description, not in a new file type.
- **Section-marker convention in brainstorms (Option C).** Rejected at direction-lock; not revisiting.

## Hand-off

Walking Q1–Q7 next, then locking decisions and sketching Phase 4 (likely 2-3 tasks: brainstorm-rules update + ralph-task skill update + docs sweep).

---

## Addendum: decisions locked + Phase 4 sketch (added 2026-06-14)

### Why

Walked Q1–Q7 with confirmation by the user on each. Direction A (Distill) holds. The 7 locks below converge on a single coherent task — producer/consumer discipline between brainstorm-rules and ralph-task, plus three additional surfaces (ralph-review, task-reviewer-rules, README) for defense-in-depth and discoverability.

### What changed (Q1–Q7 locks)

**Q1 — Distillation depth (locked):** Maximum. The entire Phase 3 addendum (locked decisions + per-Q reasoning + scope cuts + AC list + implementation checklist) is copied verbatim into the task `-d`. Task is fully self-sufficient; implementer never reads the brainstorm.

**Q2 — Where discipline lives (locked):** Producer/consumer split (Option C). Brainstorm-rules Save Design Conclusions sections (Case A + Case B addendum) mandate a named **"Distilled for ralph-task"** block as a producer responsibility — the brainstorm author writes it once when locking Phase 3 decisions. Ralph-task lifts that block verbatim into `-d` as the consumer responsibility. A self-check in ralph-task greps for `design/.*-brainstorm\.md` patterns in the resulting task body and warns on any match.

**Q3 — ralph-review changes (locked):** Soft warning. ralph-review continues reading brainstorm/PRD as intent source. Adds a check: grep each in-scope task `-d` for `design/.*-brainstorm\.md`; emit one warning line per match in the final chat report ("Warning: TASK-NNN references brainstorm file in description — distillation may have been skipped"). Does NOT block the review. Cheap insurance against pipeline regressions; won't fire if Q2 holds.

**Q4 — PRD layer for multi-task features (locked):** Author judgment with a one-line heuristic in brainstorm-rules Phase 4 Override: *"If the feature is multi-task AND the brainstorm captures cross-task invariants (shared interface contract, ordering constraint, shared invariant the reviewer must check across tasks), generate a PRD via ralph-prd. Single-task or independent-sibling work needs only per-task distillation."* No coded threshold; trust authors.

**Q5 — Migration of existing tasks (locked):** Leave alone. TASK-139 and TASK-140 stay as filed under the old convention. The new convention applies forward to the first task filed after this change merges. Backfill is high lift, near-zero value.

**Q6 — Edge cases (locked):** No separate rule. The distillation rule is additive to ralph-task's existing MUST #2 ("description may include code blocks for verbatim implementer use"). Forbids design-rationale file references; leaves inline-code-blocks allowance untouched.

**Q7 — Files-to-update inventory (locked):**

| File | Change |
|---|---|
| `.claude/brainstorm-rules.md` | Save Design Conclusions Case A + Case B addendum gain mandatory "Distilled for ralph-task" block; Phase 4 Override gets PRD-fallback heuristic |
| `skills/ralph-init/templates/claude/brainstorm-rules.md` | Same edits (R11 pair; pre-`## Project additions` region byte-identical) |
| `skills/ralph-task/SKILL.md` | New MUST rule forbidding `design/.*-brainstorm\.md` in `-d`; canonical pattern updated to "copy verbatim from brainstorm's distilled block"; self-check grep |
| `skills/ralph-review/SKILL.md` | Q3 soft-warning logic added to the final chat report step |
| `skills/ralph-prd/SKILL.md` | One-line "when to invoke" clarifier matching the Q4 heuristic |
| `.claude/task-reviewer-rules.md` | New project-specific rule: task `-d` must not contain `design/.*-brainstorm\.md`. (Per project memory: do NOT mirror to ralph-init templates — task-reviewer-rules is project-specific.) |
| `README.md` | Section 1 mentions distilled-block convention; Section 1→2 transition explains when ralph-prd vs direct-to-ralph-task; Section 5 mentions Q3 soft warning |

### Phase 4 — task AC sketch

Single task. By Q4's own heuristic this is multi-file but **not** multi-task (one purpose-value: introduce distillation discipline; producer/consumer changes ship together or not at all per the Rollback rule).

Task title (English): **Distill brainstorm conclusions into tasks; forbid brainstorm-file refs in task descriptions**

Feature label: `feature:brainstorm-to-task-handoff` (matches this brainstorm file slug).

Acceptance criteria (9 — under the 10 cap, all objectively pass/fail):

1. `.claude/brainstorm-rules.md` Save Design Conclusions sections (Case A + Case B addendum) gain a mandatory named "Distilled for ralph-task" output block. The block specifies the structure: locked decisions list (one per line), 1-sentence rationale each, scope cuts, AC sketch, implementation checklist.
2. `.claude/brainstorm-rules.md` Phase 4 Override gains the one-line PRD-fallback heuristic verbatim from Q4 lock above.
3. `skills/ralph-init/templates/claude/brainstorm-rules.md` is byte-identical to `.claude/brainstorm-rules.md` for the pre-`## Project additions` region (R11 parity verified by `diff` on that region producing no output).
4. `skills/ralph-task/SKILL.md` adds the consumer-side discipline: new MUST rule forbidding `design/.*-brainstorm\.md` in task `-d`; canonical pattern updated to document "copy the verbatim 'Distilled for ralph-task' block"; mandatory self-check greps for the forbidden pattern in the resulting task body and warns.
5. `skills/ralph-review/SKILL.md` Step 6 (Report to Chat) gains soft-warning logic: greps each in-scope task `-d` for `design/.*-brainstorm\.md`; for each match, prepends one warning line to the chat output ("Warning: TASK-NNN references brainstorm file in description — distillation may have been skipped"). Does NOT block the review.
6. `skills/ralph-prd/SKILL.md` adds a one-line "when to invoke" clarifier matching the brainstorm-rules Phase 4 Override heuristic.
7. `.claude/task-reviewer-rules.md` adds a new project-specific rule: task `-d` must not contain `design/.*-brainstorm\.md`. Rule body explains: distillation is the producer/consumer convention; brainstorm-file refs in `-d` violate that independence.
8. `README.md` Section 1 (Brainstorm) mentions the distilled-block convention; Section 1→2 transition adds a branch hint distinguishing ad-hoc work (skip to ralph-task) from PRD-shaped work (ralph-prd → ralph-backlog) per the Q4 heuristic; Section 5 (Cumulative review) mentions the Q3 soft warning.
9. Smoke verification documented in task Implementation Notes: file a scratch ad-hoc task containing a `design/X-brainstorm.md` reference; confirm ralph-task self-check warns; confirm task-reviewer-rules would surface the violation pre-merge; confirm ralph-review's chat-output greps for and emits the warning.

### Implementation checklist

- Edit `.claude/brainstorm-rules.md` Save Design Conclusions Case A — AC 1.
- Edit `.claude/brainstorm-rules.md` Save Design Conclusions Case B addendum — AC 1.
- Edit `.claude/brainstorm-rules.md` Phase 4 Override — AC 2.
- Mirror to `skills/ralph-init/templates/claude/brainstorm-rules.md` — AC 3.
- Edit `skills/ralph-task/SKILL.md` MUST rules + canonical pattern + self-check section — AC 4.
- Edit `skills/ralph-review/SKILL.md` Step 6 — AC 5.
- Edit `skills/ralph-prd/SKILL.md` — AC 6.
- Edit `.claude/task-reviewer-rules.md` — AC 7. Do NOT mirror to ralph-init templates (per project memory).
- Edit `README.md` Sections 1, 1→2 transition, 5 — AC 8.
- Smoke check — AC 9.
- Verify R11 parity with `diff <(sed '/^## Project additions/,$d' .claude/brainstorm-rules.md) <(sed '/^## Project additions/,$d' skills/ralph-init/templates/claude/brainstorm-rules.md)` (must produce no output).
- After merge: run `/ralph-sync` to propagate skill changes to user-global.

### Out of scope (final, locked)

- Replacing brainstorm-rules.md wholesale (only Save Design Conclusions + Phase 4 Override change).
- Forcing PRD generation for every feature (rejected at direction-lock).
- Auto-rewriting existing Done tasks (Q5 lock).
- Tooling: extraction script that pulls "distilled" sections out of brainstorm files (manual discipline suffices).
- Adding a new `design/<name>-spec.md` or `decisions.md` file kind (distillation lives in task `-d`, not in a new file kind).
- Section-marker convention in brainstorms / Option C (rejected at direction-lock).
- task-reviewer-rules mirrored to ralph-init templates (per project memory).
- CLAUDE.md / AGENTS.md changes (neither contains workflow content).

---

## Distilled for ralph-task

> Producer block per Q2 lock. ralph-task copies this section verbatim into the new task's `-d`. Eating our own dogfood — this is the format the new convention prescribes for every future brainstorm.

**Direction:** A (Distill). Phase 4 hand-off does NOT reference the brainstorm file. Locked decisions + rationale + scope cuts + AC list are copied verbatim into the task description. Brainstorm becomes pure human-design history. Reviewer continues reading brainstorm as intent; task is the contract; independence preserved because they are different artifacts.

**Locked decisions (with rationale):**

- **Q1 Maximum distillation** — entire Phase 3 addendum copied verbatim. *Rationale:* makes the task fully self-sufficient; implementer (human or AI) never needs to open the brainstorm.
- **Q2 Producer/consumer split** — brainstorm-rules writes a named "Distilled for ralph-task" block; ralph-task copies it verbatim + self-checks no brainstorm-file refs leak into `-d`. *Rationale:* clear contract between two skills; backstop catches future hand-edits.
- **Q3 Soft warning** — ralph-review greps in-scope task `-d` for `design/.*-brainstorm\.md` and emits one warning line per match; does not block. *Rationale:* post-hoc detection of pipeline regressions; cheap; won't fire if Q2 holds.
- **Q4 PRD optional by heuristic** — multi-task features with cross-task invariants generate PRD via ralph-prd; single-task or independent-sibling work uses per-task distillation only. *Rationale:* keeps lightweight ralph-task flow intact; PRD layer for cases that need it; author judgment.
- **Q5 No migration** — TASK-139 and TASK-140 stay as filed. *Rationale:* historical artifacts; new convention applies forward; backfill is low value.
- **Q6 Additive rule** — distillation does not displace ralph-task's existing inline-code-blocks allowance. *Rationale:* code snippets and design rationale are different content kinds; both rules coexist.
- **Q7 Seven-file inventory** — brainstorm-rules (live + R11 template), ralph-task, ralph-review, ralph-prd, task-reviewer-rules, README. *Rationale:* defense-in-depth (3 enforcement points: create-time, pre-merge, post-merge) + discoverability (README) + producer-spec discipline (brainstorm-rules).

**Scope cuts:**

- Replacing brainstorm-rules.md wholesale.
- Forcing PRD for every feature.
- Auto-rewriting existing Done tasks.
- Extraction script tooling.
- New file kinds (`design/<name>-spec.md`).
- Section-marker convention in brainstorms.
- Mirroring task-reviewer-rules to ralph-init templates.
- CLAUDE.md / AGENTS.md edits.

**Acceptance criteria:** see "Phase 4 — task AC sketch" above (9 ACs).

**Implementation checklist:** see above.
