# Brainstorm: ralph-task

Replace the user-global `project-manager-backlog` agent with a thin project-level `ralph-task` skill for one-off / ad-hoc backlog task creation outside the PRD/brainstorm-driven feature pipeline.

## Architecture decision

Drop `~/.claude/agents/project-manager-backlog.md` entirely. Replace its narrow Ralph-project role with `skills/ralph-task/SKILL.md`. The agent's defects (comma-joined `--ac` examples in 4 places, "code snippets should be avoided" guidance, no post-create self-verification) reflect a mental-model conflict with autonomous Ralph execution, not surface typos. A skill is right-sized: on-demand loading (no permanent context cost), lives next to other ralph-* skills, single point of maintenance.

The lens distinction: `ralph-backlog` is bulk, PRD-driven, `feature:<name>`-labeled. `ralph-task` is one or a few ad-hoc tasks (defects, chores, small fixes), label optional. They do not overlap.

## Components / flows

### `skills/ralph-task/SKILL.md` (new)

- **Triggers** — "create a task", "add a task", "new task", "track this as a task", "log a task"
- **Pre-checks (delegate when out of lane):**
  - PRD-shaped ask → propose `ralph-prd` → `ralph-backlog`
  - Open exploration → propose `brainstorm`
- **Canonical `backlog task create` pattern** with three MUST rules:
  1. **Repeat `--ac` per criterion.** The CLI does NOT split on commas (`--ac "a,b"` creates ONE AC).
  2. **Description may include code blocks** when an implementer needs the exact snippet (regex, bash pipeline, SQL). Override the generic "WHY without HOW" — Ralph runs autonomously and can't re-derive.
  3. **`feature:<slug>` label optional.** Default off; attach when the task is a missed/follow-on item for an existing feature. If user names a feature, verify `design/<name>-prd.md` or `design/<name>-brainstorm.md` exists; warn if not.
- **6-rule decomposition heuristic** — see table below.
- **Mandatory self-check after create** — `backlog task view <id> --plain | grep -A20 Acceptance`; if collapsed ACs found, fix with `backlog task edit <id> --remove-ac N --ac "..." --ac "..."`.

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

## Open questions

- **Routing in Phase 4 for feature-shaped brainstorms.** Today's chosen approach (Path C) — "rule names ralph-task; skill self-routes via pre-check" — relies on a vague pre-check ("PRD-shaped: multiple user stories, feature with broad scope"). For v2, tighten the pre-check with concrete signals: ≥3 tasks predicted by the 6 rules, ≥3 components in different lanes, presence of "feature/US-N/non-goals" keywords, or intent to run `/ralph-review` later. Deferred from v1 — current vague heuristic is good enough for the cases we've actually hit.
- **Cross-project skill portability.** The `ralph-task` skill is project-level (lives in this repo's `skills/`). User-global propagation happens via ralph-sync after merge. If another non-Ralph project wants the same skill, they'd copy the folder. Open: should ralph-init (which bootstraps Ralph in a new project) include `ralph-task` in its skill seed list? Out of scope for v1; revisit when ralph-init parity is next reviewed.
- **Cadence detection.** "Autonomous Ralph favors 5–7 ACs; human-led runs closer to 10" is documented in the cadence note but not detected. The skill doesn't know whether the invocation is in a Ralph loop or interactive. v2 could read `MODE: autonomous` from the prompt and tighten the cap dynamically. Deferred.

## Hand-off

Per Rule 0 (purpose-value), implementation is **one backlog task**: "Replace project-manager-backlog with ralph-task skill in Ralph workflow." Single user-visible deliverable: the Ralph project uses `ralph-task` for ad-hoc task creation; the buggy agent is gone.

Acceptance criteria (target ~7 ACs):

1. `skills/ralph-task/SKILL.md` exists with frontmatter, triggers, pre-checks, canonical create pattern (3 MUST rules), 6-rule decomposition heuristic with cadence note, mandatory self-check
2. `.claude/brainstorm-rules.md` Phase 4 rule names `ralph-task` skill explicitly (text matches the wording in the brainstorm doc above)
3. `CLAUDE.md` Task Lifecycle section has the 2-line pointer to ralph-task / ralph-prd→ralph-backlog
4. `~/.claude/agents/project-manager-backlog.md` is deleted (`ls` confirms no file)
5. `ralph-sync classify` returns `[new]` for `skills/ralph-task/SKILL.md` before sync
6. After sync, `~/.claude/skills/ralph-task/SKILL.md` exists and `ralph-sync classify` returns `[unchanged]`
7. Smoke test: a fresh Claude conversation invoking "create a task to fix typo X" routes to ralph-task (no fall-back to project-manager-backlog, since the agent is gone)

Next: skip ralph-prd (single-skill scope, no PRD warranted) → directly create the implementation task via the new pattern (bootstrap case — apply the skill's documented `backlog task create` pattern manually, since the skill doesn't exist yet at task-creation time).
