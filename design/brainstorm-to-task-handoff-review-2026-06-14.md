# Feature Review: brainstorm-to-task-handoff (2026-06-14)

**Verdict: Aligned**

**Passes run:** Pass 1 (intent-coverage), Pass 3 (scope-cut compliance), Pass 5 (drift)
**Passes skipped:** Pass 2 (no PRD; brainstorm has no separate "Non-Goals" section beyond scope cuts handled in Pass 3), Pass 4 (no PRD; brainstorm has no "Success Metrics" section)

No custom rules file present (`.claude/ralph-review-rules.md` absent).

Authoritative intent = `design/brainstorm-to-task-handoff-brainstorm.md` (Q1–Q7 locked decisions in the 2026-06-14 addendum + 9 ACs in the Phase 4 sketch). No PRD exists. Diff range: `20d54d1..HEAD` (3 commits; 8 files; 344 insertions / 6 deletions). TASK-141 is the only in-scope task.

## Intent → Implementation Matrix

### Q1–Q7 Locked Decisions

| ID | Lock | Status | Evidence |
|----|------|--------|----------|
| Q1 | Maximum distillation — entire Phase 3 addendum copied verbatim into task `-d` | Delivered | `backlog/tasks/task-141 …md` lines 19-91: task `-d` contains Direction, Q1–Q7 locks with rationale, Scope cuts, Implementation checklist verbatim from brainstorm addendum |
| Q2 | Producer/consumer split with named "Distilled for ralph-task" block + ralph-task self-check | Delivered | Producer: `.claude/brainstorm-rules.md:28-47` (Case A) and `:69-88` (Case B) define the block. Consumer: `skills/ralph-task/SKILL.md:79` (MUST rule #4) + `:128-141` (Check 2 self-check) |
| Q3 | Soft warning at review time (no block) | Delivered | `skills/ralph-review/SKILL.md:208-225` Step 6a — grep + per-task warning line, "MUST NOT alter the verdict or block the review" |
| Q4 | PRD optional by author judgment heuristic | Delivered | `.claude/brainstorm-rules.md:109` Phase 4 Override carries the verbatim Q4 heuristic ("multi-task AND brainstorm captures cross-task invariants… single-task or independent-sibling…") |
| Q5 | No migration; new convention applies forward | Delivered | `.claude/task-reviewer-rules.md:206-207` R16 "Excluded" clause lists "Pre-existing Done tasks (e.g., TASK-139, TASK-140)" as historical artifacts |
| Q6 | Additive rule; inline code blocks still allowed | Delivered | `skills/ralph-task/SKILL.md:55` canonical pattern retains "may include code blocks for verbatim implementer use"; MUST rule #4 supplements but does not displace #2 |
| Q7 | Seven-file inventory shipped | Delivered | git diff stat hits exactly the 7 file paths from the lock table |

### Acceptance Criteria (Phase 4 sketch, 9 ACs)

| AC | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| AC1 | Case A + Case B addendum gain mandatory "Distilled for ralph-task" block with required structure (5 elements) | Delivered | `.claude/brainstorm-rules.md:28-47` and `:69-88`. Both list Direction, Locked decisions with rationale, Scope cuts, Acceptance criteria sketch, Implementation checklist |
| AC2 | Phase 4 Override gains verbatim Q4 PRD-fallback heuristic | Delivered | `.claude/brainstorm-rules.md:109` carries the Q4 lock wording verbatim |
| AC3 | R11 parity: template byte-identical to live for pre-`## Project additions` region | Delivered | Independently verified at HEAD: `diff <(git show HEAD:.claude/brainstorm-rules.md \| sed '/^## Project additions/,$d') <(git show HEAD:skills/ralph-init/templates/claude/brainstorm-rules.md \| sed '/^## Project additions/,$d')` exits 0 with empty output |
| AC4 | ralph-task adds MUST rule #4 + canonical-pattern update + self-check grep | Delivered | `skills/ralph-task/SKILL.md:60` ("Four MUST rules"); `:79` rule #4 forbids `design/.*-brainstorm\.md`; `:55` canonical `-d` pattern documents the verbatim-paste; `:128-141` Check 2 self-check |
| AC5 | ralph-review Step 6 soft warning grep + per-match warning prepended to chat output, does not block | Delivered | `skills/ralph-review/SKILL.md:208-225` Step 6a "Distillation soft-warning scan" plus `:235-241` chat-output template. See reviewer-notes section for per-match vs per-task nuance |
| AC6 | ralph-prd adds one-line "when to invoke" clarifier matching Q4 | Delivered | `skills/ralph-prd/SKILL.md:21` carries the Q4 heuristic verbatim |
| AC7 | task-reviewer-rules adds project-specific rule with rationale; NOT mirrored to templates | Delivered | `.claude/task-reviewer-rules.md:183-208` adds R16 with rationale, reproducible grep, exclusion clause, and explicit non-mirror note citing `feedback_rules_not_in_ralph_init.md`. No diff to `skills/ralph-init/templates/claude/task-reviewer-rules.md` |
| AC8 | README Section 1 + 1→2 transition + Section 5 updates | Delivered | `README.md:91` Section 1 mentions distilled-block contract; `:93-97` new 1→2 transition; `:212` Section 5 mentions Q3 soft warning |
| AC9 | Smoke verification documented; reproducible | Delivered | `backlog/tasks/task-141 …md:103-151` documents scratch TASK-142 procedure with verbatim commands and outputs for all three enforcement points. Scratch archive removed |

## Scope Cut Violations

None detected. Cross-checked all eight locked scope cuts (Save Design Conclusions wholesale rewrite, forced PRD generation, auto-rewriting Done tasks, extraction tooling, new `design/<name>-spec.md` file kind, section-marker convention, mirroring task-reviewer-rules to ralph-init templates, CLAUDE.md/AGENTS.md changes) against the diff. All compliant.

## Drift List

No drift detected within the diff range. Every hunk traces to one of AC1–AC9. Master-branch-guard hook untouched (`diff <(git show HEAD:.claude/hooks/master-branch-guard.sh) .claude/hooks/master-branch-guard.sh` → empty, exit 0).

## Reviewer Notes

1. **Cross-skill regex coherence.** Identical regex `design/.*-brainstorm\.md` used in all four enforcement surfaces: `skills/ralph-task/SKILL.md` (lines 79, 131, 285), `skills/ralph-review/SKILL.md` (lines 211, 217), `.claude/task-reviewer-rules.md` (lines 183, 196), `README.md` (line 212). Warning message shape consistent ("Warning: TASK-NNN references … distillation may have been skipped").

2. **R11 parity holds.** Independently verified via the exact strip-and-diff command from the task notes.

3. **Hook revert paranoia.** `master-branch-guard.sh` byte-identical to HEAD's blob. No hook revert.

4. **R7 commit cleanliness.** All three task commits (`c44fbd4`, `4c2c966`, `ee44b65`) free of `Co-Authored-By`, "Generated with Claude Code", and `## Test plan` headings.

5. **Eat-our-own-dogfood note.** TASK-141's own `-d` contains five matches of the forbidden regex (lines 19, 75, 105, 117, 132). All five are quoted examples of the pattern itself (anti-pattern citation, AC text defining the pattern, smoke-verification log) — not directives pointing the implementer to a brainstorm file. The R16 "Excluded" clause already handles this via reviewer judgment ("flag only when the reference is presented as a directive ('see this file') rather than as a quoted example"). Acceptable as inherent rule edge case. Future hardening options if wanted: (a) refine regex to require a leading `see |Source:|reference:|conclusions:` keyword, (b) introduce an `<!-- R16-exempt: reason -->` opt-out marker. Both belt-and-suspenders only.

6. **Smoke verification quality.** TASK-142 fully purged: `git ls-files | grep -i task-142` empty, `find . -name '*task-142*'` empty, `git diff 20d54d1..HEAD --name-only | grep -i task-142` empty.

7. **AC#5 nuance — "per match" vs "per task".** Brainstorm Q3 and AC#5 say "emit one warning line per match", but Step 6a uses `grep -qE` inside a per-task `for id in` loop, emitting at most one warning per task even if multiple matches. Task-reviewer accepted this since the warning message shape is per-task. Not blocking; flagged for future tightening to `grep -nE | while read … do echo Warning …` if strict per-match emission desired.

8. **Working-tree drift (out-of-scope but flagged).** Post-merge working tree has uncommitted reverts to `.claude/brainstorm-rules.md` and `.claude/task-reviewer-rules.md` that undo TASK-141's feature work — Distilled blocks deleted, Phase 4 Override stripped, R16 rule removed. Merge commit `ee44b65` is correct; templates intact (so ralph-init bootstraps unaffected). But if these reverts were committed, the feature would unship on the live project. This is the **third recurrence** of the same pattern (TASK-137, TASK-139, TASK-141 — all Ralph-driven merges). Recommended: `git restore .claude/brainstorm-rules.md .claude/task-reviewer-rules.md`, then file a chore task to investigate the recurrence source (likely devcontainer mount or post-merge Ralph hook behavior).

9. **Operational follow-up.** After-merge `/ralph-sync` propagation to user-global `~/.claude/skills/` is documented as a post-merge step in TASK-141 notes. Worth flagging to the user as an outstanding action.

Relevant absolute file paths:
- `/Users/paul/Private/Projects/ai/ralph/design/brainstorm-to-task-handoff-brainstorm.md`
- `/Users/paul/Private/Projects/ai/ralph/.claude/brainstorm-rules.md`
- `/Users/paul/Private/Projects/ai/ralph/.claude/task-reviewer-rules.md`
- `/Users/paul/Private/Projects/ai/ralph/skills/ralph-init/templates/claude/brainstorm-rules.md`
- `/Users/paul/Private/Projects/ai/ralph/skills/ralph-task/SKILL.md`
- `/Users/paul/Private/Projects/ai/ralph/skills/ralph-review/SKILL.md`
- `/Users/paul/Private/Projects/ai/ralph/skills/ralph-prd/SKILL.md`
- `/Users/paul/Private/Projects/ai/ralph/README.md`
- `/Users/paul/Private/Projects/ai/ralph/backlog/tasks/task-141 - Distill-brainstorm-conclusions-into-tasks-forbid-brainstorm-file-refs-in-task-descriptions.md`
