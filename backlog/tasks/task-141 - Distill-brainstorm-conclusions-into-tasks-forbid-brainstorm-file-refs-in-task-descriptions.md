---
id: TASK-141
title: >-
  Distill brainstorm conclusions into tasks; forbid brainstorm-file refs in task
  descriptions
status: Done
assignee: []
created_date: '2026-06-14 07:22'
updated_date: '2026-06-14 07:47'
labels:
  - 'feature:brainstorm-to-task-handoff'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Across the recent feature:ralph-init-hook-ordering, the Phase 4 hand-off pattern was: task description includes a line like "Design conclusions: design/<name>-brainstorm.md". Two consumers then read that file: (a) autonomous Ralph implementing the task, (b) ralph-reviewer judging alignment. Three failure modes follow — token cost (brainstorm grows during the walk; ~10K tokens read every iteration), evolution mismatch (early-doc options superseded by late-doc addendum can mislead an LLM weighting surface area), and review-independence collapse (Ralph and reviewer reading the same doc reduces the review to "Ralph copied faithfully").

DIRECTION (locked): Option A — Distill. Phase 4 hand-off does NOT reference the brainstorm file. Locked decisions + rationale + scope cuts + AC list are copied verbatim into the task `-d`. Brainstorm becomes pure human-design history. Reviewer continues reading brainstorm/PRD as intent; task is the contract; independence preserved because they are different artifacts.

LOCKED DECISIONS (Q1–Q7, with rationale):

- Q1 Maximum distillation — entire Phase 3 addendum copied verbatim into the task `-d`. Rationale: makes the task fully self-sufficient; implementer (human or AI) never needs to open the brainstorm.

- Q2 Producer/consumer split — `.claude/brainstorm-rules.md` Save Design Conclusions sections (Case A + Case B addendum) mandate a named "Distilled for ralph-task" output block; ralph-task copies that block verbatim into `-d` and runs a self-check greping for forbidden brainstorm-path references. Rationale: clear contract between two skills; backstop catches future hand-edits.

- Q3 Soft warning at review time — `skills/ralph-review/SKILL.md` Step 6 greps each in-scope task `-d` for `design/.*-brainstorm\.md` and emits one warning line per match in the final chat report; does NOT block the review. Rationale: post-hoc detection of pipeline regressions; cheap; will not fire if Q2 holds.

- Q4 PRD optional by author judgment — `.claude/brainstorm-rules.md` Phase 4 Override adds a one-line heuristic: "If the feature is multi-task AND the brainstorm captures cross-task invariants (shared interface contract, ordering constraint, shared invariant the reviewer must check across tasks), generate a PRD via ralph-prd. Single-task or independent-sibling work needs only per-task distillation." Rationale: keeps lightweight ralph-task flow intact; PRD layer for cases that need it.

- Q5 No migration — existing Done tasks (TASK-139, TASK-140) that reference brainstorm files stay as filed. New convention applies forward. Rationale: historical artifacts; backfill low value.

- Q6 Additive rule — the new no-brainstorm-ref MUST rule does NOT displace ralph-task MUST rule #2 ("description may include code blocks for verbatim implementer use"). Inline code blocks remain allowed. Rationale: code snippets and design rationale are different content kinds.

- Q7 Seven-file inventory — see implementation checklist below. Defense-in-depth (3 enforcement points: ralph-task at create, task-reviewer-rules pre-merge, ralph-review post-merge) + discoverability (README) + producer-spec discipline (brainstorm-rules).

SCOPE CUTS (final, locked):

- Replacing brainstorm-rules.md wholesale.
- Forcing PRD generation for every feature.
- Auto-rewriting existing Done tasks.
- Tooling: extraction script that pulls "distilled" sections out of brainstorm files (manual discipline suffices).
- Adding a new `design/<name>-spec.md` or `decisions.md` file kind.
- Section-marker convention in brainstorms (Option C; rejected at direction-lock).
- task-reviewer-rules.md mirrored to ralph-init templates (per project memory `feedback_rules_not_in_ralph_init.md`).
- CLAUDE.md / AGENTS.md changes (neither contains workflow content).

IMPLEMENTATION CHECKLIST (maps to ACs):

- Edit `.claude/brainstorm-rules.md` — Save Design Conclusions Case A + Case B addendum gain the "Distilled for ralph-task" output block; Phase 4 Override gains the PRD-fallback heuristic.
- Mirror to `skills/ralph-init/templates/claude/brainstorm-rules.md` (R11 pair for pre-`## Project additions` region).
- Edit `skills/ralph-task/SKILL.md` — new MUST rule forbidding `design/.*-brainstorm\.md` in `-d`; canonical pattern updated; mandatory self-check grep.
- Edit `skills/ralph-review/SKILL.md` Step 6 — add soft-warning logic.
- Edit `skills/ralph-prd/SKILL.md` — one-line "when to invoke" clarifier matching Q4 heuristic.
- Edit `.claude/task-reviewer-rules.md` — add project-specific rule. Do NOT mirror to ralph-init templates.
- Edit `README.md` Sections 1, 1→2 transition, 5.
- Smoke verify the three enforcement points.
- After merge: run /ralph-sync to propagate skill changes to user-global.

R11 parity check: `diff <(sed "/^## Project additions/,\$d" .claude/brainstorm-rules.md) <(sed "/^## Project additions/,\$d" skills/ralph-init/templates/claude/brainstorm-rules.md)` must produce no output.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `.claude/brainstorm-rules.md` Save Design Conclusions Case A + Case B addendum both gain a mandatory named "Distilled for ralph-task" output block; the block specifies the structure: locked decisions list (one per line), 1-sentence rationale each, scope cuts, AC sketch, implementation checklist
- [x] #2 `.claude/brainstorm-rules.md` Phase 4 Override gains the verbatim PRD-fallback heuristic from the locked Q4 (single-task or independent-sibling work uses per-task distillation; multi-task with cross-task invariants generates a PRD)
- [x] #3 `skills/ralph-init/templates/claude/brainstorm-rules.md` is byte-identical to live `.claude/brainstorm-rules.md` for the pre-`## Project additions` region (R11 parity; verified by sed-strip diff producing no output)
- [x] #4 `skills/ralph-task/SKILL.md` adds a new MUST rule forbidding `design/.*-brainstorm\.md` in task `-d`; canonical pattern documents "copy the verbatim Distilled for ralph-task block from the brainstorm"; mandatory self-check greps the resulting task body for the forbidden pattern and warns on any match
- [x] #5 `skills/ralph-review/SKILL.md` Step 6 (Report to Chat) gains soft-warning logic: greps each in-scope task `-d` for `design/.*-brainstorm\.md`; emits one warning line per match in the final chat output; does NOT block the review
- [x] #6 `skills/ralph-prd/SKILL.md` adds a one-line "when to invoke" clarifier matching the Q4 heuristic — single-task or independent-sibling work skips PRD; multi-task with cross-task invariants uses PRD
- [x] #7 `.claude/task-reviewer-rules.md` adds a new project-specific rule: task `-d` must not contain `design/.*-brainstorm\.md`. Rule body explains the producer/consumer convention. Rule is NOT mirrored to `skills/ralph-init/templates/claude/task-reviewer-rules.md` (per project memory: task-reviewer-rules is project-specific)
- [x] #8 `README.md` Section 1 (Brainstorm) mentions the distilled-block convention; Section 1→2 transition adds a branch hint distinguishing ad-hoc work (skip to ralph-task) from PRD-shaped work (ralph-prd → ralph-backlog) per the Q4 heuristic; Section 5 (Cumulative review) mentions the Q3 soft warning
- [x] #9 Smoke verification documented in task Implementation Notes: file a scratch ad-hoc task containing a `design/X-brainstorm.md` reference; confirm ralph-task self-check warns; confirm task-reviewer-rules rule would surface the violation pre-merge; confirm ralph-review chat-output greps for and emits the warning. Document reproducible invocation
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation

Seven files touched (matches Q7 inventory):

1. `.claude/brainstorm-rules.md` — Case A template gains "## Distilled for ralph-task" subsection; Case B addendum template gains "### Distilled for ralph-task"; "In both cases" prose explains the producer/consumer contract; Phase 4 Override gains the PRD-fallback heuristic.
2. `skills/ralph-init/templates/claude/brainstorm-rules.md` — same edits, byte-identical pre-`## Project additions` (R11 parity verified).
3. `skills/ralph-task/SKILL.md` — canonical pattern updated; MUST rules expanded from 3 to 4 (rule #4 forbids `design/.*-brainstorm\.md` in `-d`); self-check section split into Check 1 (AC splitting) + Check 2 (brainstorm-ref grep); stopping-checklist updated.
4. `skills/ralph-review/SKILL.md` — Step 6 split into 6a (distillation soft-warning scan) + 6b (verdict and drift). Warnings prepended to chat output; never block.
5. `skills/ralph-prd/SKILL.md` — added "When to invoke (vs. going straight to `ralph-task`)" clarifier matching the Q4 heuristic.
6. `.claude/task-reviewer-rules.md` — added R16 (after R15) with full rationale and a reproducible grep. NOT mirrored to ralph-init templates per project convention.
7. `README.md` — Section 1 mentions the distilled-block contract; new 1→2 transition explains the PRD-vs-ralph-task branch; Section 5 mentions the soft warning.

## R11 parity (AC #3)

Verified by:

```bash
diff <(sed '/^## Project additions/,$d' .claude/brainstorm-rules.md) <(sed '/^## Project additions/,$d' skills/ralph-init/templates/claude/brainstorm-rules.md)
```

Output: empty (parity OK).

## Smoke verification (AC #9) — reproducible

Created scratch TASK-142 with `-d` referencing `design/sample-brainstorm.md`, then ran each enforcement point's grep; all three fired. Scratch archive removed afterwards (it would have been an R16 violation in the diff if kept).

### Enforcement 1 — ralph-task self-check (Check 2)

```bash
backlog task view 142 --plain | grep -nE 'design/.*-brainstorm\.md' \
  && echo "WARN: TASK-142 description references a brainstorm file — distillation may have been skipped. Replace the reference with the verbatim 'Distilled for ralph-task' block from the source brainstorm before merge." \
  || echo "OK: no brainstorm-file refs in TASK-142 -d"
```

Output:
```
12:This scratch task intentionally references design/sample-brainstorm.md to trigger the three enforcement points...
WARN: TASK-142 description references a brainstorm file — distillation may have been skipped. Replace the reference with the verbatim 'Distilled for ralph-task' block from the source brainstorm before merge.
```

### Enforcement 2 — task-reviewer R16 scan (pre-merge)

```bash
echo "backlog/tasks/task-142 - SCRATCH-brainstorm-ref-smoke-check-delete-me.md" | while IFS= read -r f; do
  grep -nE 'design/.*-brainstorm\.md' "$f" \
    && echo "R16 violation: $f references a brainstorm file in its description"
done
```

Output:
```
15:This scratch task intentionally references design/sample-brainstorm.md to trigger the three enforcement points...
R16 violation: backlog/tasks/task-142 - SCRATCH-brainstorm-ref-smoke-check-delete-me.md references a brainstorm file in its description
```

### Enforcement 3 — ralph-review Step 6a (post-merge soft warning)

```bash
for id in 142; do
  if backlog task view "$id" --plain | grep -qE 'design/.*-brainstorm\.md'; then
    echo "Warning: TASK-\$id references a brainstorm file in its description — distillation may have been skipped"
  fi
done
```

Output:
```
Warning: TASK-142 references a brainstorm file in its description — distillation may have been skipped
```

All three enforcement points work as specified. After verification, `backlog task archive 142` then `rm backlog/archive/tasks/task-142*` removed all trace of the scratch from the diff.

## Post-merge

After merge to master, run `/ralph-sync` to propagate skill changes (ralph-task, ralph-review, ralph-prd) to user-global `~/.claude/skills/`.

Commit: `c44fbd4` - task-141: Distill brainstorm conclusions into tasks; forbid brainstorm-file refs in -d

task-reviewer: APPROVED. Reviewer flagged two non-blocking notes — (1) dangling memory citation to feedback_rules_not_in_ralph_init.md resolved by creating that memory file; (2) AC #5 wording 'per match' vs per-task implementation accepted as-is since the warning message format ('Warning: TASK-NNN references…') is naturally per-task and the brainstorm Q3 lock example uses the same per-task shape.
<!-- SECTION:NOTES:END -->
