# Feature Review: ralph-task

**Verdict: Aligned**

**Passes run:** 3, 5
**Passes skipped:** 1 (no PRD), 2 (no PRD / no Non-Goals section), 4 (no PRD / no Success Metrics section)

## Scope Cut Violations

Pass 3 verified all nine brainstorm scope cuts against the cumulative diff:

| # | Scope cut | Status | Evidence |
|---|---|---|---|
| 1 | No agent fix-in-place (replacement, not patch) | Honored | The agent file is deleted (AC #6, verified by `ls ~/.claude/agents/project-manager-backlog.md` → "No such file"). No diff hunk patches the agent's `--ac` examples; replacement via new `skills/ralph-task/SKILL.md` instead. |
| 2 | No README workflow change | Honored | Diff touches only `.claude/brainstorm-rules.md`, `CLAUDE.md`, `backlog/tasks/task-112*.md`, `skills/ralph-init/templates/root/CLAUDE.md`, and the new `skills/ralph-task/SKILL.md`. README.md has zero hunks. |
| 3 | No `ralph-prd` / `ralph-backlog` changes | Honored | Diff has no hunks under `skills/ralph-prd/` or `skills/ralph-backlog/`. |
| 4 | No multi-feature batching in ralph-task | Honored | SKILL.md "Pre-checks" section explicitly redirects PRD-shaped asks (≥3 user stories, multiple lanes) to `ralph-prd` → `ralph-backlog` rather than batching. The brainstorm-rules.md update reinforces this with the same redirect language. |
| 5 | No ralph-sync logic change | Honored | Diff has no hunks under `skills/ralph-sync/` (only the round-trip was *exercised*, per AC #7, not modified). |
| 6 | Line-count caps dropped from rule 1 | Honored | SKILL.md rule 1 row reads "~10 ACs soft cap. Beyond that, two purpose-values are bundled — split." No line-count cap appears anywhere in the heuristic table or cadence note. |
| 7 | No mechanical edit ops in skill (CLAUDE.md remains canonical) | Honored | SKILL.md "Mechanical operations — NOT this skill's lane" subsection enumerates `--check-ac`, `-s`, `--append-notes`, `--add-label`, `--priority`, `-t`, `--dep` and redirects to CLAUDE.md. The skill never documents them as its own recipes. |
| 8 | Edit triggers are conversational, not action-shaped | Honored | The "Edit-deliberation triggers" table lists conversational phrasings ("should I split this task", "scope grew", "is this AC clear"). The "Non-triggers" subsection explicitly excludes mechanical action verbs ("edit task 110 status to Done", "mark AC 3 done", "отредактируй задачу"). |
| 9 | Trigger description is language-agnostic (English + Russian examples) | Honored | The frontmatter `description` opens with "Matching is by **semantic intent in any natural language**, not exact keyword." and provides both English and Russian example sets for both creation and edit-deliberation triggers. The Triggers section repeats the same structure. |

**None detected.**

## Drift List

Pass 5 scanned every diff hunk for traceability against the brainstorm and TASK-112 ACs:

| Hunk | Traceability |
|---|---|
| `.claude/brainstorm-rules.md` Phase 4 first option | AC #4 + brainstorm "Wiring into existing workflows" |
| `CLAUDE.md` Task Lifecycle pointer (replaces `project-manager-backlog` reference with `ralph-task` / `ralph-prd` → `ralph-backlog` pointers) | AC #5 + brainstorm "Wiring" |
| `backlog/tasks/task-112*.md` (status flip, AC checkboxes, Implementation Notes section) | Task lifecycle bookkeeping for TASK-112 itself |
| `skills/ralph-init/templates/root/CLAUDE.md` (drops `project-manager-backlog` reference, no `ralph-task` pointer added) | Stale-reference cleanup. Per user-memory, `task-reviewer-rules.md` is project-specific and must NOT be mirrored to ralph-init templates — same principle here: removing the dead reference is correct, NOT adding a `ralph-task` pointer is correct. Footgun-prevention only, in scope. |
| `skills/ralph-task/SKILL.md` (new, 214 lines) | ACs #1, #2, #3, #8, #9, #10 + brainstorm "Components / flows" |

**No drift detected.** Every hunk maps to either a TASK-112 AC, a brainstorm component/wiring item, or routine task-lifecycle bookkeeping. The `skills/ralph-init/templates/root/CLAUDE.md` cleanup is the only change not enumerated by an AC, but it is a directly traceable footgun-prevention follow-on (removing a reference to a now-deleted user-global agent from the bootstrap template) and is documented in the implementation notes.

## Reviewer Notes

- **Implementation completeness vs. brainstorm.** The brainstorm specified one task and the diff delivers it cleanly through TASK-112 (Done, all 10 ACs checked). The SKILL.md weight (214 lines) sits at the upper end of the brainstorm's "~60-80 lines" rough estimate from the task description; this is acceptable because the brainstorm itself grew the surface area (path-fence rule, edit-deliberation section with three recipes, dual-language triggers) after the original sizing. Length here reflects real content, not bloat.
- **Brainstorm ↔ SKILL.md fidelity.** The 6-rule decomposition table in SKILL.md is a verbatim copy of the brainstorm's table (rule numbers, names, signals, cadence note all match). The three MUST rules in the canonical pattern are preserved verbatim. The path-fence writing rule is reproduced with the same rationale (task-validator hook + fenced-code skip behavior).
- **Init template cleanup is a sensible follow-on.** The diff removes `project-manager-backlog` from `skills/ralph-init/templates/root/CLAUDE.md` without replacing it with a `ralph-task` pointer. This is consistent with the user-memory note that project-specific skills should not be mirrored to `ralph-init` templates — a new bootstrap consumer can re-add the pointer if/when they adopt the skill.
- **Open questions from brainstorm remain open (correctly).** v2 items — tightening the PRD-shaped pre-check, ralph-init seeding decision, autonomous-cadence detection — are not implemented in the diff. The brainstorm explicitly defers them, so their absence is correct, not drift.
- **task-reviewer evidence.** TASK-112's implementation notes record "task-reviewer agent: APPROVED" before status flip to Done, satisfying the CLAUDE.md gate. The cumulative review confirms the per-task review's approval at the feature level.
- **Single-task feature caveat.** Because this feature shipped as one task, this cumulative review and the task-reviewer review largely overlap in the change set examined. The cumulative lens still added value by checking each brainstorm scope cut against the diff (Pass 3) — that check is outside the per-task reviewer's remit.
