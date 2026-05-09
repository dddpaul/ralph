# Brainstorm: ralph-task

Replace the user-global `project-manager-backlog` agent with a thin project-level `ralph-task` skill for one-off / ad-hoc backlog task creation outside the PRD/brainstorm-driven feature pipeline.

## Architecture decision

Drop `~/.claude/agents/project-manager-backlog.md` entirely. Replace its narrow Ralph-project role with `skills/ralph-task/SKILL.md`. The agent's defects (comma-joined `--ac` examples in 4 places, "code snippets should be avoided" guidance, no post-create self-verification) reflect a mental-model conflict with autonomous Ralph execution, not surface typos. A skill is right-sized: on-demand loading (no permanent context cost), lives next to other ralph-* skills, single point of maintenance.

The lens distinction: `ralph-backlog` is bulk, PRD-driven, `feature:<name>`-labeled. `ralph-task` is one or a few ad-hoc tasks (defects, chores, small fixes), label optional. They do not overlap.

**Scope:** the skill covers task **creation** AND **judgment-bearing edits** (mid-flight decisions about adding ACs, splitting growing tasks, reworking vague ACs). Mechanical edits (`--check-ac`, status changes, `--append-notes`, `--dep`) stay in CLAUDE.md as canonical; the skill never owns them. Triggers separate the two: creation phrasings ("create a task") fire the create flow; conversational deliberation phrasings ("should I split this", "scope grew", "is this AC clear") fire the edit flow. Mechanical action verbs ("edit task 110 status to Done") deliberately do NOT trigger the skill.

## Components / flows

### `skills/ralph-task/SKILL.md` (new)

- **Creation triggers** — "create a task", "add a task", "new task", "track this as a task", "log a task"
- **Edit-deliberation triggers (judgment moments)** — "should I split this task", "scope grew", "should I add this as an AC or new task", "is this AC clear / verifiable", "rework this AC", "this fix belongs to TASK-X or its own". Mechanical action verbs ("edit task 110 status to Done", "mark AC 3 done") deliberately do NOT trigger; they redirect to CLAUDE.md.
- **Pre-checks (delegate when out of lane):**
  - PRD-shaped ask → propose `ralph-prd` → `ralph-backlog`
  - Open exploration → propose `brainstorm`
- **Canonical `backlog task create` pattern** with three MUST rules:
  1. **Repeat `--ac` per criterion.** The CLI does NOT split on commas (`--ac "a,b"` creates ONE AC).
  2. **Description may include code blocks** when an implementer needs the exact snippet (regex, bash pipeline, SQL). Override the generic "WHY without HOW" — Ralph runs autonomously and can't re-derive.
  3. **`feature:<slug>` label optional.** Default off; attach when the task is a missed/follow-on item for an existing feature. If user names a feature, verify `design/<name>-prd.md` or `design/<name>-brainstorm.md` exists; warn if not.
- **6-rule decomposition heuristic** — see table below. Applies equally to creation (one task or many?) and edit-deliberation (add as AC or split into sibling task?).
- **Editing existing tasks (judgment moments)** — when an edit-deliberation trigger fires, apply the 6 rules:
  - Rule 0 (purpose-value): is the new outcome part of the existing task's deliverable, or its own deliverable?
  - Rule 1 (one-PR / ~10 ACs): would adding this push the task over the cap?
  - Rule 5 (verification): is each AC objectively pass/fail? Reword or split any vague AC.
  - **Decision recipes:** "split into sibling task" → use the canonical create pattern above with `--dep <existing>` if needed. "Add as AC" → `backlog task edit <id> --ac "<atomic outcome>"`. For mechanical operations (status, append-notes, AC checkbox flips), redirect to CLAUDE.md — the skill does not own them.
- **Mandatory self-check after create** — `backlog task view <id> --plain | grep -A20 Acceptance`; if collapsed ACs found, fix with `backlog task edit <id> --remove-ac N --ac "..." --ac "..."`.
- **Writing rule (skill self-protection)** — when the SKILL.md itself documents paths to files that don't yet exist (e.g., `skills/ralph-task/SKILL.md` referenced from inside `skills/ralph-task/SKILL.md` during pre-merge state, or future deliverables in worked examples), keep those paths inside fenced code blocks. The task-validator hook's path-existence check skips fenced code, avoiding false positives. Plain prose mentions of yet-to-exist paths trigger validator warnings.

### Decomposition heuristic (load-bearing for the skill)

| # | Rule | Signal |
|---|---|---|
| 0 | **Purpose-value** (highest) | One task = one user-visible deliverable. Intermediate artifacts (regenerated files, format conversions, mirror updates) are ACs, not tasks. Test: "If only step N shipped, would the user have anything they asked for?" |
| 1 | One-PR | ~10 ACs soft cap. Beyond that, two purpose-values are bundled — split. |
| 2 | Dependency | Cross-purpose-value reference → split + `--dep`. Same-purpose-value reference → keep together. |
| 3 | Mirror (R11) | Mechanical mirror in parity location → same task. |
| 4 | Rollback | Partial merge breaks coherence → same task. |
| 5 | Verification | Every AC objectively pass/fail (grep, test, `bash -n`, file existence). |

**Cadence note.** Autonomous Ralph loops favor smaller tasks (5–7 ACs typical). Human-led work runs closer to ~10 cap. Same heuristic; different soft cap on rule 1.

### Wiring into existing workflows

- **`.claude/brainstorm-rules.md` Phase 4 rule** — first option rephrased: *"Create backlog task(s) — invoke the `ralph-task` skill with the brainstorm context (selected approach, ACs, testing strategy)."* (Was implicit `project-manager-backlog` grab.)
- **`CLAUDE.md` Task Lifecycle** — add ~2 lines: *"For one-off / ad-hoc task creation, use `ralph-task` ('create a task' / 'add a task'). For PRD-driven feature decomposition, use `ralph-prd` then `ralph-backlog`."*
- **`ralph-prd` / `ralph-backlog`** — unchanged. Different lanes.
- **README.md Workflow** — unchanged. ralph-task is an off-ramp for ad-hoc work, not a pipeline step.
- **`~/.claude/agents/project-manager-backlog.md`** — deleted. User-global, but user confirmed they only used it on this Ralph project; non-Ralph projects can copy the skill or recreate a fixed agent if the need arises.
- **ralph-sync** — no logic change. Auto-picks up the new `skills/ralph-task/` folder.

## Scope cuts

Decisions made during the brainstorm dialogue, recorded so future readers can verify the implementation honored them.

- **No agent fix-in-place.** Considered patching the 4 buggy `--ac` examples and dropping the "code snippets should be avoided" line. Rejected: the bugs reflect a mental-model conflict with autonomous Ralph, not surface typos. Replacement is cleaner.
- **No README workflow change.** ralph-task is an ad-hoc off-ramp, not part of the feature shipping pipeline (brainstorm → ralph-prd → ralph-backlog → ralph-run → ralph-review). Mentioning it would muddy the README's main-flow narrative.
- **No ralph-prd / ralph-backlog changes.** Their lanes don't overlap; ralph-task complements rather than replaces.
- **No multi-feature batching in ralph-task.** The skill creates 1–N tasks per invocation but never tries to be ralph-backlog. If the ask grows feature-shaped, the pre-check stops and proposes ralph-prd → ralph-backlog.
- **No ralph-sync logic change.** Sync's `agents/` ↔ `~/.claude/agents/` and `skills/` ↔ `~/.claude/skills/` mapping handles the new skill folder automatically; no special-case code.
- **Line-count caps dropped from rule 1.** Number of ACs is the actionable signal; line count varies wildly with format (a 30-line drawio XML edit ≠ 30 lines of TypeScript).
- **No mechanical edit ops in skill.** `--check-ac`, status changes, `--append-notes`, `--dep`, `--add-label`, `--priority`, `-t` (rename), and direct Edit-tool description tweaks stay in CLAUDE.md as the canonical reference. The skill never duplicates them. Rationale: CLAUDE.md is always loaded (zero overhead); routing mechanical ops through a skill would burn context for no judgment gain. Trigger separation enforces this — mechanical action verbs don't fire the skill.
- **Edit triggers are conversational, not action-shaped.** "Edit task 110" doesn't trigger; "should I split task 110?" does. Rationale: judgment is most valuable BEFORE the action; once `backlog task edit` runs with a vague AC, the task is polluted. The skill is the deliberation companion, not the executor.

## Open questions

- **Routing in Phase 4 for feature-shaped brainstorms.** Today's chosen approach (Path C) — "rule names ralph-task; skill self-routes via pre-check" — relies on a vague pre-check ("PRD-shaped: multiple user stories, feature with broad scope"). For v2, tighten the pre-check with concrete signals: ≥3 tasks predicted by the 6 rules, ≥3 components in different lanes, presence of "feature/US-N/non-goals" keywords, or intent to run `/ralph-review` later. Deferred from v1 — current vague heuristic is good enough for the cases we've actually hit.
- **Cross-project skill portability.** The `ralph-task` skill is project-level (lives in this repo's `skills/`). User-global propagation happens via ralph-sync after merge. If another non-Ralph project wants the same skill, they'd copy the folder. Open: should ralph-init (which bootstraps Ralph in a new project) include `ralph-task` in its skill seed list? Out of scope for v1; revisit when ralph-init parity is next reviewed.
- **Cadence detection.** "Autonomous Ralph favors 5–7 ACs; human-led runs closer to 10" is documented in the cadence note but not detected. The skill doesn't know whether the invocation is in a Ralph loop or interactive. v2 could read `MODE: autonomous` from the prompt and tighten the cap dynamically. Deferred.

## Hand-off

Per Rule 0 (purpose-value), implementation is **one backlog task** (TASK-112): "Replace project-manager-backlog with ralph-task skill in Ralph workflow." Single user-visible deliverable: the Ralph project uses `ralph-task` for ad-hoc task creation AND for judgment-bearing edit deliberations; the buggy agent is gone; mechanical edits remain canonical in CLAUDE.md.

Acceptance criteria (10):

1. `skills/ralph-task/SKILL.md` exists with valid YAML frontmatter (name: ralph-task, description with creation triggers: create a task / add a task / new task / track this as a task)
2. SKILL.md documents the canonical `backlog task create` pattern with three MUST rules: repeated `--ac` flags, code blocks allowed in `-d`, `feature:<slug>` label optional with design-doc sanity check
3. SKILL.md documents the 6-rule decomposition heuristic: 0 Purpose-value, 1 One-PR (~10 ACs cap), 2 Dependency, 3 Mirror (R11), 4 Rollback, 5 Verification — plus the cadence note (autonomous 5–7, human ~10)
4. SKILL.md documents the mandatory self-check after create: `backlog task view <id> --plain | grep -A20 Acceptance` and the fix recipe `backlog task edit <id> --remove-ac N --ac ... --ac ...`
5. SKILL.md "Editing existing tasks" section exists with conversational deliberation triggers (split task / scope grew / AC unclear / belongs to TASK-X), applies the 6 rules with decision recipes (split-into-sibling vs add-as-AC), and explicitly redirects mechanical ops to CLAUDE.md
6. SKILL.md documents the writing-rule path-fence convention: paths to created-on-merge files go inside fenced code blocks to avoid task-validator false-positive flags
7. `.claude/brainstorm-rules.md` Phase 4 first option text is updated to explicitly name the `ralph-task` skill (replacing the implicit project-manager-backlog grab)
8. `CLAUDE.md` Task Lifecycle section contains a 1–2 line pointer: ralph-task for ad-hoc + edit deliberation, ralph-prd then ralph-backlog for PRD-driven feature work
9. `~/.claude/agents/project-manager-backlog.md` is deleted (verifiable: `ls ~/.claude/agents/project-manager-backlog.md` returns "No such file")
10. After merge, `bash .claude/skills/ralph-sync/sync.sh classify` shows `skills/ralph-task/SKILL.md` as `[new]` before sync, `[unchanged]` after

Next: skip ralph-prd (single-skill scope, no PRD warranted) → TASK-112 is the implementation task. Worked manually via the canonical `backlog task create` pattern at brainstorm time (bootstrap case — the skill didn't exist yet at task-creation time). Existing TASK-112 to be edited to grow from 8 to 10 ACs (adds the editing section AC and the path-fence writing rule AC).
