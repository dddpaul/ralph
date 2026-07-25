---
export: true
title: 'Brainstorm: ralph-review'
type: design
---

# Brainstorm: ralph-review

Cumulative cross-task review skill and agent. Distinct lens from the existing per-task task-reviewer.

## Architecture decision

Two new pieces, one folder convention.

- **`/ralph-review` skill** — orchestrates pre-conditions, scope resolution, diff-range derivation, agent invocation, output persistence.
- **`ralph-reviewer` agent** — applies a 5-pass rubric to score the bundle of completed tasks against upstream intent. Spawned by the skill, never used standalone.
- **`design/` folder** — canonical location for upstream-intent docs. Replaces the current `tasks/` convention, which collides semantically with `backlog/tasks/`. Naming is suffix-style: `<name>-prd.md`, `<name>-brainstorm.md`, `<name>-review-<YYYY-MM-DD>.md`. The slug `<name>` is the load-bearing identifier across brainstorm, PRD, backlog labels (`feature:<name>`), and review filenames.

The lens distinction is the load-bearing rationale. `task-reviewer` is per-task, rule-driven, diff-vs-AC. `ralph-review` is per-feature, intent-driven, brainstorm/PRD-vs-bundle. They do not overlap. `ralph-review` assumes per-task review already passed (else those tasks would not be `Done`).

## Components / flows

### Inputs

| File / source | Role |
|---|---|
| `design/<name>-brainstorm.md` | Architecture + scope-cut rationale. Optional. |
| `design/<name>-prd.md` | Goals, US-N, FR-N, non-goals, success metrics. Optional. |
| In-scope backlog tasks | Title, description, ACs (with check states), implementer notes. |
| `git diff <base>..HEAD` | Cumulative shipped diff. |

At least one of brainstorm or PRD must exist (pre-condition), but both are optional individually.

### Scope determination (Approach D)

- Default: `backlog task list -l feature:<name> -s Done --plain`. ralph-backlog is responsible for labeling each task it creates with `feature:<name>` derived from the PRD filename.
- Override: explicit `tasks=N,M,K` for ad-hoc subsets or unlabeled legacy tasks.

### Diff base derivation

The post-commit hook appends `Commit: <hash>` lines to each task file. `ralph-review` walks in-scope task files, collects commit hashes, picks the earliest's parent. Works retroactively, no pre-tagging needed. `<head>` is current `HEAD`.

### Rubric (5 passes)

| Pass | Required input | Behavior if input missing |
|---|---|---|
| 1. PRD coverage | PRD | Skipped, output notes the skip |
| 2. Non-goal protection | PRD `Non-Goals` section | Skipped silently |
| 3. Brainstorm scope cuts | brainstorm | Skipped, output notes the skip |
| 4. Success-metric realism | PRD `Success Metrics` | Skipped silently |
| 5. Out-of-scope creep | either intent doc | Always runs |

Verdict only weighs passes that ran. With brainstorm-only inputs, passes 3 + 5 carry the verdict. With PRD-only, passes 1 + 2 + 4 + 5.

### Verdict aggregation (3-bucket)

- **Aligned** — every US/FR `delivered`; no non-goal violations; no scope-cut contradictions; out-of-scope creep < 10% of diff lines.
- **Partial** — at least one US/FR `partial` or `missing`; no non-goal violations; no scope-cut contradictions.
- **Drifted** — any non-goal violation OR any scope-cut contradiction OR > 30% of diff lines are out-of-scope creep.

### Output

Saved to `design/<name>-review-<YYYY-MM-DD>.md`. Suffix `-NN` on filename collision (`-01`, `-02`); never overwrites. Contains:

1. Verdict + one-paragraph rationale.
2. Intent → Implementation matrix (each US/FR/scope-cut → tasks/commits + state).
3. Drift list (creep, gaps, contradictions).
4. Reviewer notes (deferred work, open questions).

Chat output: verdict line + drift list only. Pointer to the saved file.

### Error handling

- Agent crash / timeout → "review failed: <reason>"; no fabricated verdict.
- Diff exceeds context → spawn agent in chunks per PRD section, aggregate, surface `WARN`.
- Missing PRD section → skip its pass silently, log in output.

## Scope cuts

Decisions made during the brainstorm dialogue, recorded so future readers (and `ralph-review` itself) can verify the implementation honored them.

- **No numeric score (e.g. 7.4/10).** Three buckets (Aligned / Partial / Drifted) are easier to act on. Matrix and drift list carry the texture.
- **No auto-trigger at end of Ralph loop.** Manual `/ralph-review name=<name>` only. Auto-trigger would tie review timing to loop completion, but a feature spans multiple loops; the user picks the moment.
- **No PRD ↔ task explicit linkage written into task descriptions.** Linkage is by `feature:<name>` label only. Adding US-N references to each task is brittle and ralph-backlog would need re-architecting.
- **No nested per-feature folder (`design/<name>/...`).** Flat suffix style chosen for smallest delta from existing `tasks/prd-*.md` convention. Re-evaluate if `design/` accumulates many features and grouping becomes painful.
- **Brainstorm save handoff is a project-level rule, not a brainstorm modification.** brainstorm is a third-party plugin (umputun-cc-thingz). We add `.claude/brainstorm-rules.md` to instruct it via its custom-rules mechanism. We never edit brainstorm skill files.

## Open questions

- **Multi-feature reviews** — do we need `/ralph-review name=foo,bar,baz` or `--all-since=<date>`? Out of scope for v1; revisit if the workflow demands it.
- **Aggregation of prior reviews** — if `<name>` accumulates many `-review-<date>.md` files (because the feature ships in waves), should the latest review reference deltas vs the prior one? Out of scope for v1.
- **`<base>` when post-commit hook didn't fire** — task files predating the hook lack `Commit:` lines. Fallback to first-commit-on-`task-N-*` branch via `git log --grep="^task-N: "` is feasible but slow. Documented as known limitation; user can pass `tasks=` and accept full-history diff.

## Hand-off

Implementation broken into atomic backlog tasks under label `feature:ralph-review`:

- **TASK-102** — design/ folder convention; ralph-prd and ralph-backlog path updates; `feature:<name>` label.
- **TASK-103** — `.claude/brainstorm-rules.md` for save-handoff to `design/<name>-brainstorm.md`.
- **TASK-104** — `agents/ralph-reviewer.md` (new agent with rubric prompt).
- **TASK-105** — `skills/ralph-review/SKILL.md` (depends on TASK-104).
- **TASK-106** — README Workflow update with `design/` paths and `/ralph-review` step (depends on TASK-102, TASK-105).
- **TASK-107** — ralph-init upgrade migration prompt for legacy `tasks/prd-*.md` (depends on TASK-102).
- **TASK-108** — this brainstorm doc (bootstrap case, the design/ folder's first inhabitant).

Run order Ralph will follow: 102 → 103 → 104 → 105 → 106 → 107. TASK-108 is this commit.
