---
export: true
title: Ralph-init hook ordering + master-branch-guard scope
type: design
---

# Ralph-init hook ordering + master-branch-guard scope

## Context / trigger

User ran `/ralph-init` against an existing Obsidian vault project. Step 3.9 (writing `.obsidian/app.json`, `.obsidian/hotkeys.json`, `.obsidian/snippets/wide-tables.css`) was rejected by `.claude/hooks/master-branch-guard.sh`, which had been installed and activated just two sub-steps earlier by Step 3.7a (`.claude/settings.json` write). Same ralph-init invocation; the flow self-blocked mid-bootstrap.

## Bug confirmed

### Hook scope

`.claude/hooks/master-branch-guard.sh:29-31` exempts only three patterns inside the project tree when on `master`:

- `*/.claude/*` or `.claude/*`
- `*/design/*` or `design/*`
- basename `.gitignore`

Everything else inside the project root is denied with `BLOCKED: no active task branch.`.

### Step order in `skills/ralph-init/SKILL.md`

Crossing the activation line:

| Step | Write target | Hook state | Result |
|---|---|---|---|
| 3.1 | `ralph.sh` (project root) | inactive | ✓ |
| 3.2 | `CLAUDE.md` (project root) | inactive | ✓ |
| 3.3 | `.git/hooks/*` | inactive | ✓ |
| 3.4 | `.gitignore` | (exempt) | ✓ |
| 3.5 | `backlog/` | CLI, not Write | ✓ |
| 3.6 | `.devcontainer/*` | inactive | ✓ |
| **3.7a** | `.claude/settings.json` + `.claude/hooks/*` + `.claude/settings.local.json` | (exempt, but **this step activates the hook**) | ✓ — and now hook fires |
| 3.7b/c | jq merge | Bash, not Write | ✓ |
| 3.8 | `.claude/brainstorm-rules.md` | (exempt) | ✓ |
| **3.9** | `.obsidian/app.json`, `hotkeys.json`, `snippets/wide-tables.css` | **active** | ❌ BLOCKED |
| 3.10 | verify | read-only | ✓ |

Only Step 3.9 crosses the line. That is the entire init-time bug.

## Why this matters beyond init

1. **Recurring user-edit case** — once init completes, any time a user on `master` asks Claude to tweak `.obsidian/snippets/*.css`, `.vscode/settings.json`, `.idea/*`, etc., the hook blocks. Those are editor/vault state, not source code subject to task discipline. The gitignored ones (`workspace.json`, `community-plugins.json`) can't even reach a commit, yet writes are still rejected.

2. **Latent upgrade-mode bug** — U4 overwrites `ralph.sh`, `CLAUDE.md`, `.git/hooks/*`, `.devcontainer/*`. If the user runs `ralph upgrade` on `master` with hooks already installed, every one of those writes is denied. Hasn't surfaced because upgrades typically happen from a task branch, but it is real and waiting.

## Options

### A. Reorder only — move hook activation to the end of init

Split Step 3.7a:

- Write `.claude/hooks/*.sh` (the scripts on disk) early, alongside `.claude/settings.local.json`. Inert without a settings.json reference.
- Defer the `.claude/settings.json` write — the file that *registers* the hooks with Claude Code — until after Step 3.9 (and ideally after 3.10).

**Pros:** Fixes ralph-init self-block with zero scope change to the hook. Conceptually clean: hooks come alive last.
**Cons:** Doesn't help the recurring user-edit case on master after init. Doesn't help upgrade mode. Adds an ordering invariant that future SKILL.md editors must remember.

### B. Widen exempt list — add common editor/vault dirs

Add to `.claude/hooks/master-branch-guard.sh` exempt block: `.obsidian/`, `.vscode/`, `.idea/`, `.cursor/`, `.zed/`.

**Pros:** Fixes both ralph-init Step 3.9 *and* the recurring user-edit case. Single-file change. Aligns the hook's intent (source-code discipline) with what it actually blocks.
**Cons:** Hardcoded list, not principled. Misses any editor the list doesn't enumerate. Doesn't help upgrade mode (which writes `ralph.sh`, `CLAUDE.md`, etc. — explicitly source-code-shaped paths).

### C. A + B together

Belt-and-suspenders. Reorder fixes the bootstrap; widen fixes the steady state. Upgrade-mode latent bug stays unfixed (separate consideration).

**Pros:** Two independent defenses; either alone would have prevented the reported bug; together they also cover the steady-state user-edit case.
**Cons:** Larger diff. Two cooperating mechanisms to remember.

### D. Smarter hook — exempt anything in `.gitignore`

Parse the project's `.gitignore` at hook-fire time; if the target path is gitignored, exempt it.

**Pros:** Principled. If a path can't reach a commit, task-branch discipline doesn't apply to it. Covers any editor the user adds in the future without code changes.
**Cons:** `.gitignore` parsing is non-trivial (negation patterns `!foo`, `**`, anchored vs. unanchored). Slow on large gitignores per Edit/Write call. May surprise: a freshly-added gitignore line silently widens the exempt set. Easier to get wrong than right.

### E. Self-disable during ralph-init — env-var bypass

ralph-init sets `RALPH_INIT_IN_PROGRESS=1` while running; the hook checks for it and short-circuits.

**Pros:** Surgical. Only affects the ralph-init self-block; everything else is untouched.
**Cons:** Doesn't help the recurring user-edit case or upgrade mode. Env vars don't propagate to Claude Code's hook subprocess by default. Brittle: depends on Claude Code's hook environment. Most importantly, gives the user a "go around the guard" lever that can be misused.

## Tentative recommendation

**C (A + B together).** Reorder fixes the immediate bootstrap defect; widen exempts the steady-state class of legitimate edits the user makes on master. D is conceptually cleaner but the parsing complexity isn't worth it for five well-known editor directories. E is too clever and only fixes one of three scenarios.

Upgrade-mode latent bug (ralph.sh / CLAUDE.md / .git/hooks/* / .devcontainer/* overwrites on master) is a separate concern — it cannot be fixed by widening (those paths *should* be guarded) or reordering (upgrade mode doesn't activate the hook, it runs with an already-active one). Worth a follow-on task or a separate brainstorm thread.

## Open questions

1. **Exempt list contents.** Which editor/vault dirs go in? Proposal: `.obsidian/`, `.vscode/`, `.idea/`, `.cursor/`, `.zed/`. Add `.fleet/`? `.history/`? Any concern about `.vscode/settings.json` being source-code-shaped (committed, project-wide)?

2. **Reorder shape.** Move just `.claude/settings.json` to the end, or move all of Step 3.7 (a/b/c) plus 3.10 to the end? Cleaner code vs. minimal diff.

3. **Step 3.7a split vs. delete-and-rewrite.** Two ways to "defer settings.json": (i) split 3.7a so hooks-on-disk and settings.local.json land early, settings.json lands last; (ii) write settings.json early but with hooks block empty, then overwrite with full hooks block at the end. Option (i) is cleaner.

4. **Upgrade-mode follow-up.** Same task as this fix, separate task, or a separate brainstorm? Possible options: pre-stage the writes onto a synthetic branch; require `ralph upgrade` to run from a task branch (with a preflight check); have upgrade-mode set the bypass env-var (couples to Option E).

5. **Test coverage.** Existing `tests/unit/master-branch-guard.bats` (if any — verify) needs new cases for the new exempts. Init-flow tests need a `.obsidian/` write assertion after activation.

## Scope cuts (preliminary — confirm before locking)

- Replacing master-branch-guard entirely. (No — the intent is sound; only its blast radius needs tuning.)
- Extending guard to non-master branches (e.g., also blocking direct writes on `main`). (No — out of scope for this brainstorm.)
- Reworking the "what counts as source code?" question by introducing a positive allowlist instead of an exempt list. (No — bigger architectural change; pursue separately if needed.)
- Auto-removing `.obsidian/workspace.json` etc. that the user accidentally committed pre-fix. (No — recoverable via `git rm --cached`.)
- Hook performance optimization (currently ~5ms per Edit/Write call). (No — non-issue at current scale.)

## Hand-off

Walking Q1–Q5 next, then locking decisions and sketching Phase 4 (task ACs).

---

## Addendum: decisions locked + Phase 4 sketch (added 2026-06-13)

### Why

Walked Q1–Q5. Tentative recommendation (Option C — reorder + widen) holds. Locking decisions and sketching the task ACs so this brainstorm can hand off to `ralph-task` cleanly.

### What changed

**Q1 — exempt list (locked):** six directories — `.obsidian/`, `.vscode/`, `.idea/`, `.cursor/`, `.zed/`, `.fleet/`. Skip `.history/` for now (too niche; add later if it bites). Each handled in both `*/<dir>/*` and `<dir>/*` shapes, matching the existing `.claude/` / `design/` patterns.

**Q2 — reorder shape (locked):** move *only* `.claude/settings.json` to the very end (after current Step 3.10). Smaller diff than moving all of Step 3.7, and makes the invariant durable for any future template-write step: "hook activation is the last act of init."

**Q3 — split shape (locked):** falls out of Q2 — split Step 3.7a. Keep `.claude/hooks/*.sh` and `.claude/settings.local.json` writes in the early slot; defer only `.claude/settings.json` to a new step at the end. No placeholder/overwrite dance — one final write.

**Q4 — upgrade-mode follow-up (locked):** separate sibling task, same feature family (`ralph-init-hook-ordering`), `--dep` on this task. Approach: add a U1.5-shaped preflight that refuses `ralph upgrade` on `master` unless on a task branch. Don't bundle here — keeps this PR small and the upgrade-mode fix has been latent forever, so no urgency.

**Q5 — gitignore-aware hook (rejected):** Option D dropped. Negation patterns + `**` + anchoring make `.gitignore` parsing fragile in shell; performance hits every Edit/Write call; silent widening on a new gitignore line is a footgun. The explicit six-dir list covers the realistic cases; users with exotic editor dirs can extend.

### Phase 4 — task AC sketch

Task title (English): **Reorder ralph-init hook activation + widen master-branch-guard exempt list**

Feature label: `feature:ralph-init-hook-ordering` (matches this brainstorm file slug).

Acceptance criteria (8 — under the 10 cap, all objectively pass/fail):

1. `.claude/hooks/master-branch-guard.sh` exempt block widens to also pass through six editor/vault dirs: `.obsidian/`, `.vscode/`, `.idea/`, `.cursor/`, `.zed/`, `.fleet/`. Each in both `*/<dir>/*` and `<dir>/*` shapes (matching existing `.claude/` / `design/` patterns at lines 29-30).
2. Header comment block of `.claude/hooks/master-branch-guard.sh` (lines 2-3) updated to enumerate the new exempts so a reader sees the full exempt set without grepping the case statement.
3. `skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` is byte-identical to live `.claude/hooks/master-branch-guard.sh` (R11 parity verified by `diff` producing no output).
4. `skills/ralph-init/SKILL.md` Step 3.7a is split: writing `.claude/hooks/*.sh` and `.claude/settings.local.json` remains in the early slot; writing `.claude/settings.json` is removed from 3.7a. Step renamed if needed for clarity.
5. `skills/ralph-init/SKILL.md` adds a new step (3.11) placed after current Step 3.10 that writes `.claude/settings.json` from `templates/claude/settings.json`. The body explains *why* the activation is deferred (one-line rationale + back-pointer to this brainstorm).
6. `tests/unit/master-branch-guard.bats` (create if missing, extend if present) covers each of the six new exempt dirs with a positive case: a write under `<dir>/...` on `master` returns exit 0 with no deny JSON. Six new test bodies, one per dir.
7. Existing exempt-case tests (`.claude/`, `design/`, `.gitignore`) continue to pass; existing deny-case tests still produce the BLOCKED JSON. Confirms no regression.
8. Smoke verification: simulated end-to-end run of `/ralph-init` on a scratch repo at `master` reaches Step 3.9 (`.obsidian/*` writes) without hook denial. Document the invocation in the task's Implementation Notes.

### Implementation checklist

- Edit `.claude/hooks/master-branch-guard.sh` — AC 1, 2.
- Mirror to `skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` — AC 3.
- Edit `skills/ralph-init/SKILL.md` — split 3.7a, add 3.11 — AC 4, 5.
- Extend `tests/unit/master-branch-guard.bats` (or create it) — AC 6, 7.
- Run the smoke check — AC 8.
- Verify R11 parity with `diff .claude/hooks/master-branch-guard.sh skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` (must produce no output).
- File sibling task — "Refuse `ralph upgrade` on master unless on a task branch" — with `--dep` on this task and label `feature:ralph-init-hook-ordering`. Don't bundle.

### Out of scope (final, locked)

- Replacing master-branch-guard entirely.
- Extending the guard to non-master branches.
- Switching from exempt-list to positive-allowlist architecture.
- Auto-cleaning `.obsidian/workspace.json` etc. accidentally committed pre-fix.
- Hook performance optimization.
- Upgrade-mode preflight (sibling task — see Q4 above).
- `.history/` exempt (deferred until requested).
