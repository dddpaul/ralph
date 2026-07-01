---
name: ralph-task
description: "Create one or a few ad-hoc backlog tasks (defects, chores, small fixes) outside the PRD/brainstorm pipeline, AND deliberate judgment-bearing edits to existing tasks (split / add as AC / rework vague AC). Matching is by **semantic intent in any natural language**, not exact keyword. English creation triggers: create a task, add a task, new task, track this as a task, log a task. Russian creation triggers: создай задачу, добавь задачу, новая задача, оформи задачу. English edit-deliberation triggers: should I split this task, scope grew, AC unclear, this belongs to TASK-X. Russian edit-deliberation triggers: разбить задачу, расширилась задача, AC размытый, переложить в отдельную задачу. Mechanical action verbs (edit task X status to Done, mark AC 3 done, отредактируй задачу) deliberately do NOT trigger — they are owned by CLAUDE.md."
---

# Ralph Task Creator & Edit-Deliberation Companion

Thin skill for ad-hoc backlog work. Two lanes:

1. **Create** one or a few backlog tasks outside the PRD/brainstorm pipeline.
2. **Deliberate** mid-flight judgment calls on existing tasks (split, add as AC, rework vague AC).

This skill complements — does not replace — `ralph-prd` → `ralph-backlog` (PRD-driven feature decomposition). It also does NOT own mechanical edits (`--check-ac`, status changes, `--append-notes`, `--add-label`, `--priority`, `-t` rename, `--dep`); those stay in CLAUDE.md.

---

## Triggers

Matching is **by semantic intent in any natural language**, not exact keyword. Other languages match the same intent without requiring a re-listing of variants.

### Creation triggers

| Language | Examples |
|---|---|
| English | "create a task", "add a task", "new task", "track this as a task", "log a task" |
| Russian | "создай задачу", "добавь задачу", "новая задача", "оформи задачу" |

### Edit-deliberation triggers (judgment moments)

| Language | Examples |
|---|---|
| English | "should I split this task", "scope grew", "should I add this as an AC or new task", "is this AC clear / verifiable", "rework this AC", "this fix belongs to TASK-X or its own" |
| Russian | "разбить задачу", "расширилась задача", "AC размытый", "переложить в отдельную задачу" |

### Non-triggers (redirect to CLAUDE.md)

Mechanical action verbs: "edit task 110 status to Done", "mark AC 3 done", "append note to task 5", "отредактируй задачу 7", "set priority high on task 9". These are routine `backlog task edit` operations — apply directly per CLAUDE.md, without invoking this skill.

---

## Pre-checks (delegate when out of lane)

Before creating, classify the ask:

- **PRD-shaped** (≥3 user stories, multiple lanes, broad scope) → propose `ralph-prd` → `ralph-backlog` instead.
- **Open exploration** ("what could we do about X?", "should we even build this?") → propose `brainstorm` first.
- **One or a few well-formed asks** → continue with the create flow.

---

## Canonical `backlog task create` pattern

```bash
backlog task create "<English title>" \
  -d "<WHY paragraph; for brainstorm hand-offs, paste the verbatim 'Distilled for ralph-task' block from the source brainstorm; may include code blocks for verbatim implementer use>" \
  --ac "<atomic outcome 1>" \
  --ac "<atomic outcome 2>" \
  --priority <high|medium|low>
```

When the task originates from a brainstorm Phase 4 hand-off, the `-d` body MUST be the verbatim "Distilled for ralph-task" block from the source brainstorm (`design/<slug>-brainstorm.md` or its addendum). Copy it as-is — Direction, Locked decisions with rationale, Scope cuts, Acceptance criteria sketch, Implementation checklist. Do NOT replace it with a sentence like *"see design/<slug>-brainstorm.md"*. The distillation is the contract; the brainstorm itself is human-design history.

### Four MUST rules

1. **MUST: repeat `--ac` per criterion.** The CLI does NOT split on commas. `--ac "a,b,c"` creates **one** AC literally containing the commas, not three. Repeat the flag once per criterion.

2. **MUST: description may include code blocks.** Override any generic "WHY without HOW" guidance — autonomous Ralph runs without the original conversation context and cannot re-derive a regex, bash pipeline, SQL fragment, or specific command. If the implementer needs the exact snippet, embed it inside a fenced block in `-d`.

3. **MUST: `feature:<slug>` label is optional.** Default off. Attach `-l "feature:<name>"` only when the task is a missed/follow-on item for an existing feature. If the user names a feature, **verify** that one of the design docs exists before attaching the label:

   ```bash
   ls design/<name>-prd.md design/<name>-brainstorm.md 2>/dev/null
   ```

   If neither exists, warn the user and ask whether to (a) skip the label, (b) create the design doc first via `ralph-prd`, or (c) attach anyway as a stub.

   **Brainstorm Phase 4 hand-off (default ON):** If the skill is invoked with a `feature=<slug>` arg, attach `-l "feature:<slug>"` automatically to every task created in this invocation. Skip the verify-prompt — the brainstorm-rules "Save Design Conclusions" rule already wrote and verified the design file (`design/<slug>-brainstorm.md` or its addendum) before the Phase 4 hand-off. Treat the slug as authoritative; do NOT re-run the `ls design/<slug>-*` check. The label is required downstream so `/ralph-review feature=<slug>` can find every task that belongs to the feature for cumulative consistency checks.

4. **MUST: task `-d` MUST NOT reference brainstorm files.** Description body MUST NOT contain a path matching `design/.*-brainstorm\.md`. Brainstorm files are human-design history; tasks are the contract for the implementer (human or autonomous Ralph). When a task description points at a brainstorm file, three failure modes follow: (a) token cost — the implementer reads ~10K tokens of brainstorm every iteration; (b) evolution mismatch — early-doc options superseded by late-doc addenda mislead the implementer; (c) review-independence collapse — `ralph-review` reads the brainstorm as intent and the implementer reads it as the contract, so review degenerates to "Ralph copied the doc faithfully." Distill the locked decisions + rationale + scope cuts + AC sketch + implementation checklist verbatim into `-d` instead. The producer half of this contract lives in `.claude/brainstorm-rules.md` ("Distilled for ralph-task" block); this rule is the consumer half.

### Title language constraint

Task titles passed to `backlog task create` must be in **English** — the CLI derives filenames from the title. The description (`-d`) and acceptance criteria (`--ac`) may be in any language.

---

## 6-rule decomposition heuristic

Applies equally to creation ("one task or many?") and edit-deliberation ("add as AC or split into sibling task?").

| # | Rule | Signal |
|---|---|---|
| 0 | **Purpose-value** (highest) | One task = one user-visible deliverable. Intermediate artifacts (regenerated files, format conversions, mirror updates) are **ACs**, not tasks. Test: "If only step N shipped, would the user have anything they asked for?" |
| 1 | One-PR | ~10 ACs soft cap. Beyond that, two purpose-values are bundled — split. |
| 2 | Dependency | Cross-purpose-value reference → split + `--dep`. Same-purpose-value reference → keep together. |
| 3 | Mirror (R11) | Mechanical mirror in parity location → same task. |
| 4 | Rollback | Partial merge breaks coherence → same task. |
| 5 | Verification | Every AC objectively pass/fail (grep, test, `bash -n`, file existence). |

### Cadence note

Autonomous Ralph loops favor smaller tasks (**5–7 ACs typical**). Human-led work runs closer to **~10 cap**. Same heuristic; different soft cap on rule 1.

---

## Mandatory self-check (after create)

Immediately after `backlog task create` returns an ID, run two checks.

### Check 1 — AC splitting

Verify the ACs were actually split:

```bash
backlog task view <id> --plain | grep -A20 "Acceptance"
```

Read each AC line. If a single AC line contains commas joining what should be separate atomic outcomes, fix in one command:

```bash
backlog task edit <id> --remove-ac N --ac "<split outcome 1>" --ac "<split outcome 2>"
```

This catches the historical defect where comma-joined `--ac "a,b,c"` collapsed multiple intended criteria into one literal AC.

### Check 2 — no brainstorm-file references in `-d`

Verify MUST rule #4. Grep the full task view for the forbidden pattern:

```bash
backlog task view <id> --plain | grep -nE 'design/.*-brainstorm\.md' \
  && echo "WARN: TASK-<id> description references a brainstorm file — distillation may have been skipped. Replace the reference with the verbatim 'Distilled for ralph-task' block from the source brainstorm before merge." \
  || echo "OK: no brainstorm-file refs in TASK-<id> -d"
```

If the grep matches, edit the task to remove the reference and inline the distilled block:

```bash
backlog task edit <id> -d "<verbatim Distilled for ralph-task block, no design/<slug>-brainstorm.md reference>"
```

Re-run the grep until it reports OK. The same rule is enforced post-merge as `task-reviewer` rule R16 and surfaced as a soft warning by `ralph-review`; catching it here keeps the contract clean from the start.

---

## What next? (after create)

Immediately after the mandatory self-check passes — and **before** any branch creation, implementation, or skill-stop — surface a structured choice to the user instead of silently proceeding into interactive implementation. Use the `AskUserQuestion` tool. This is the create-lane instance of the universal **Implementation Mode Gate** in CLAUDE.md; both default to **Ralph** (option 1, Recommended).

### The 4-option block (single task)

- **Question stem:** `Task TASK-<id> created. What next?`
- **Header:** `What next?`

| # | Label | Description | Action on selection |
|---|---|---|---|
| 1 | Ralph now (Recommended) | "I launch /ralph-run tasks=<id> watch=5m in the devcontainer." | Invoke `/ralph-run tasks=<id> watch=5m devcontainer=true`. Do NOT pre-set status — Ralph manages it |
| 2 | Interactive now | "I branch, implement, review, merge in this session." | `backlog task edit <id> -s "In Progress"` → `git checkout -b task-<id>` → CLAUDE.md Task Lifecycle steps 2–6 |
| 3 | Continue chatting | "Task waits in To Do; you decide later." | One-line acknowledgment. No state change |
| 4 | Other | "Type your own — e.g., 'ralph 1,2 not 3 without watch', 'interactive but skip review'." | Ask one clarifying question, then act. If still ambiguous after the clarification → fall back to option 3 |

### Multi-task variant

When the same trigger turn produced multiple tasks (a batch dictated in one breath), fire **one** prompt covering the batch, not one per task.

- **Question stem:** `Tasks TASK-<id1>, TASK-<id2>, ... created. What next?`
- **Header:** `What next?`
- **Option 1 description switches to:** `/ralph-run tasks=<id1>,<id2>,... watch=5m`

The four labels stay the same. Action mapping for option 1 passes the comma-joined task list to `/ralph-run` (still with `devcontainer=true`).

### Skip condition (no prompt fires)

If the trigger turn already contained an unambiguous execution-mode verb, skip the prompt and act directly. Bar for skip is high: a verb that **names the execution mode**. Bare implementation verbs ("...and start it", "implement X", "fix it now") do NOT name a mode — they fire the prompt (which defaults to Ralph), matching the universal Implementation Mode Gate in CLAUDE.md. Vague tails ("...and we'll see") also fire the prompt.

| Intent in trigger turn | Action without prompting |
|---|---|
| "...and ralph it" / "run it with ralph" / "автономно" | Option 1 (Ralph) path |
| "...implement it interactively" / "do it here in this session" | Option 2 (Interactive) path |
| "...for later" / "just log it" / "на потом" | Option 3 path |

### Defensive defaults

- **AskUserQuestion failure or parse error → fall back to option 3** (no-op + one-line acknowledgment). Never silently launch Ralph and never silently branch.
- **`devcontainer=true` is passed explicitly to `/ralph-run`** even though it is the current default — defends against future skill-default flips. Devcontainer isolation is safety-critical (firewall, file boundary). Other launch knobs (model, effort, timeout, max_iterations) are left implicit and inherited from `/ralph-run`.
- **Edit-deliberation lane does NOT fire this prompt.** Only the create lane does. Recipes A/B/C in the "Editing existing tasks" section below run their own state changes inline and stop without asking.

---

## Editing existing tasks (judgment moments)

When an edit-deliberation trigger fires, apply the 6 rules to decide between two recipes:

### Decision: split into sibling task vs. add as new AC

- **Rule 0 (purpose-value):** Is the new outcome part of the existing task's deliverable, or its own deliverable? Different deliverable → split.
- **Rule 1 (one-PR / ~10 ACs):** Would adding this push the task over the cap? Over → split.
- **Rule 2 (dependency):** Cross-purpose-value reference → split with `--dep`. Same-purpose-value → keep.
- **Rule 5 (verification):** Is each AC objectively pass/fail? If the AC is vague ("works correctly", "good UX"), reword it to a verifiable form. If it cannot be made verifiable in one line, split it.

### Recipe A — split into sibling task

```bash
backlog task create "<new English title>" \
  -d "<WHY>" \
  --ac "<atomic outcome 1>" \
  --ac "<atomic outcome 2>" \
  --dep task-<existing-id> \
  --priority <high|medium|low>
```

Then run the mandatory self-check on the new task.

### Recipe B — add as new AC

```bash
backlog task edit <id> --ac "<atomic outcome>"
```

### Recipe C — rework vague AC

```bash
backlog task edit <id> --remove-ac N --ac "<verifiable rewrite>"
```

If the rewrite naturally splits into multiple atomic outcomes, repeat `--ac` per outcome in the same command.

### Mechanical operations — NOT this skill's lane

For routine state changes — checking off ACs (`--check-ac` / `--uncheck-ac`), status transitions (`-s "In Progress"` / `-s "Done"`), appending notes (`--append-notes`), labels (`--add-label` / `--remove-label`), priority (`--priority`), title rename (`-t`), or dependency edits (`--dep`) — apply directly per CLAUDE.md Task Lifecycle. Do NOT route through this skill.

---

## Writing rule (skill self-protection)

The task-validator hook (`.claude/hooks/task-validator.sh`) checks that backtick-quoted paths and markdown link targets exist on disk, but it **skips fenced code blocks**. When this skill or any task description references a path to a file that will only exist *after merge* (e.g., during pre-merge state, the SKILL.md may need to forward-reference its own path), keep that path inside a fenced block:

```text
skills/ralph-task/SKILL.md
```

Plain prose mentions of yet-to-exist paths trigger validator false positives. Fenced blocks are the safe channel.

---

## Quick examples

### Example 1 — single ad-hoc defect

User: "Create a task for the broken redirect on /settings."

```bash
backlog task create "Fix broken redirect on /settings" \
  -d "After the auth refactor in TASK-99, /settings redirects to /login even for authenticated users. Reproduce: log in, visit /settings, observe redirect chain. Likely cause: middleware order in app/middleware.ts." \
  --ac "Authenticated user visiting /settings sees the settings page (no redirect)" \
  --ac "Unauthenticated user visiting /settings is still redirected to /login" \
  --ac "bash -n on app/middleware.ts passes" \
  --priority high
```

Then self-check:

```bash
backlog task view <new-id> --plain | grep -A20 "Acceptance"
```

### Example 2 — edit deliberation

User: "I'm working on TASK-110 and the scope grew — should I add another AC or split?"

Apply rule 0: is the new outcome part of TASK-110's purpose-value, or its own? Apply rule 1: would TASK-110 exceed ~10 ACs? Apply rule 5: is each new AC verifiable?

If different deliverable or AC count would exceed cap → recipe A (split into sibling with `--dep task-110`).
If same deliverable and within cap → recipe B (`backlog task edit 110 --ac "<outcome>"`).

---

## Checklist before stopping

- [ ] Each `--ac` flag was repeated per criterion (no comma-joined lists)
- [ ] Description includes code blocks where the implementer needs the exact snippet
- [ ] For brainstorm hand-offs: `-d` is the verbatim "Distilled for ralph-task" block (no `design/<slug>-brainstorm.md` reference)
- [ ] `feature:<name>` label only attached after design-doc sanity check passed (or user opted in)
- [ ] Self-check 1 ran: `backlog task view <id> --plain | grep -A20 Acceptance`
- [ ] Self-check 2 ran: `backlog task view <id> --plain | grep -nE 'design/.*-brainstorm\.md'` returned no matches
- [ ] Any collapsed AC was fixed with `--remove-ac N --ac "..." --ac "..."`
- [ ] After create: AskUserQuestion fired unless skip-condition matched
- [ ] Acted on the chosen option (1/2/3/4)
- [ ] For edit-deliberation: applied rules 0/1/2/5 before choosing recipe A vs B vs C
- [ ] Mechanical ops were NOT routed through this skill
