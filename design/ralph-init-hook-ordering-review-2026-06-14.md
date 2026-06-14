# Feature Review: ralph-init-hook-ordering (cumulative, round 2 — 2026-06-14)

**Verdict: Aligned**

**Passes run:** 1 (Intent → Implementation against brainstorm Q1–Q5 + 13 ACs), 3 (Scope Cuts), 5 (Out-of-Scope Creep)
**Passes skipped:** 2 (no PRD ⇒ no "Non-Goals" section; the brainstorm's "Scope cuts" subsection is covered under Pass 3), 4 (no PRD ⇒ no "Success Metrics" section)

Authoritative intent = `design/ralph-init-hook-ordering-brainstorm.md` (Q1–Q5 locked decisions in the 2026-06-13 addendum + 8 ACs for TASK-139 + 5 ACs for TASK-140). No PRD exists for this feature. Diff range `a968a70..HEAD` spans 8 commits, 8 files, 513 insertions / 5 deletions; TASK-139 + the prior review artifact + TASK-140 + a metadata-fix housekeeping commit.

This review supersedes `design/ralph-init-hook-ordering-review-2026-06-13.md` (round 1, TASK-139 only). Round 1's Aligned verdict still holds — re-checked under cumulative scope and nothing in TASK-140 regressed it.

## Intent → Implementation Matrix

| ID | Intent (brainstorm Q-lock / AC) | Status | Evidence |
|----|----|----|----|
| Q1 | Six exempt dirs (`.obsidian/`, `.vscode/`, `.idea/`, `.cursor/`, `.zed/`, `.fleet/`), each in `*/<dir>/*` and `<dir>/*` shapes; skip `.history/` | Delivered | `.claude/hooks/master-branch-guard.sh` lines 32-37 — six `case` lines, exact shape parity with existing `.claude/` / `design/` exempts; `.history/` absent |
| Q2 | Move only `.claude/settings.json` to the very end (after Step 3.10); invariant "hook activation is the last act of init" | Delivered | `skills/ralph-init/SKILL.md` line 319 — Step 3.11 placed after 3.10; line 322 bolds the invariant verbatim and back-points to the brainstorm |
| Q3 | Split Step 3.7a: hooks + `settings.local.json` stay early, only `settings.json` defers; no placeholder/overwrite dance | Delivered | `SKILL.md` lines 173-177 — 3.7a rewritten; explanatory paragraph ties dormant scripts to 3.11; single final write, no overwrite |
| Q4 | Upgrade-mode follow-up is a separate sibling task adding a U1.5-shaped preflight that refuses `ralph upgrade` on master unless on a task branch | Delivered | TASK-140 filed with `dependencies: [TASK-139]` and `feature:ralph-init-hook-ordering` label; `SKILL.md` lines 396-422 implement the U1.5 preflight exactly as locked |
| Q5 | Option D (gitignore-aware hook) rejected; explicit list only | Delivered (by absence) | No `.gitignore`-parsing logic added to either hook copy — only literal `case` patterns |
| TASK-139 AC #1 | Exempt block widens to six dirs in both shapes | Delivered | `.claude/hooks/master-branch-guard.sh:32-37` |
| TASK-139 AC #2 | Header comment (lines 2-3) enumerates the new exempts | Delivered | Header now reads `(except .claude/, design/, .obsidian/, .vscode/, .idea/, .cursor/, .zed/, .fleet/, .gitignore)` — all nine listed verbatim |
| TASK-139 AC #3 | Template byte-identical to live hook (R11 parity) | Delivered & still holds | `diff <(git show HEAD:.claude/hooks/master-branch-guard.sh) <(git show HEAD:skills/ralph-init/templates/claude/hooks/master-branch-guard.sh)` → no output |
| TASK-139 AC #4 | Step 3.7a split: hooks + `settings.local.json` stay; `settings.json` removed | Delivered | `SKILL.md:173-177` |
| TASK-139 AC #5 | New Step 3.11 after 3.10 writes `.claude/settings.json` from template; rationale + brainstorm back-pointer | Delivered | `SKILL.md:319-322` — rationale + `design/ralph-init-hook-ordering-brainstorm.md (Options A–E, Q1–Q5, addendum 2026-06-13)` back-pointer |
| TASK-139 AC #6 | Six new positive-case bats tests, one per new exempt dir | Delivered | `tests/unit/pretools-hooks.bats` lines 143-182 — six `@test` blocks, one per dir |
| TASK-139 AC #7 | Existing exempt-case tests and deny case continue to pass | Delivered | Full bats suite 31/31 pass per TASK-139 notes; re-confirmed unchanged by TASK-140 (no test file touched in `68c4bf2`) |
| TASK-139 AC #8 | Smoke verification of `/ralph-init` reaching Step 3.9 documented | Delivered | TASK-139 Implementation Notes document the scratch-repo invocation and 3 PASS / 0 FAIL result |
| TASK-140 AC #1 | New "U1.5: Branch Safety" inserted between U1 and renamed U1.6 (Legacy Migration); cross-references updated | Delivered | `SKILL.md:396` (U1.5: Branch Safety), `SKILL.md:425` (U1.6: Legacy File Migration). Cross-references at lines 406, 419 both point to `U1.6` correctly. `grep "U1\.5\|U1\.6"` returns only the four expected lines |
| TASK-140 AC #2 | Runs `git rev-parse --abbrev-ref HEAD`, refuses on `master` or `HEAD` (detached); refusal fires before any file reads | Delivered | `SKILL.md:402` (rev-parse), `SKILL.md:406` ("If `branch` is `master` or `HEAD` (the latter indicates detached HEAD): print the refusal message verbatim and **stop**. Do NOT read any files, do NOT proceed to U1.6 or U2"), `SKILL.md:421` ("This step fires before any file reads, so a refusal has no side effects") |
| TASK-140 AC #3 | Refusal message includes concrete recovery command + re-invoke instruction | Delivered | `SKILL.md:413` — verbatim `git checkout -b task-<id>-ralph-upgrade master` + "Create a task branch first, then re-invoke upgrade"; also includes brainstorm Q4 back-pointer |
| TASK-140 AC #4 | On non-master/non-detached branches, behavior unchanged from existing U1.6 onward | Delivered | `SKILL.md:419` — "proceed silently to U1.6"; no edits to U1.6/U2/U3/U4/U5 bodies in the diff (only the section header rename at line 425) |
| TASK-140 AC #5 | Smoke verification documented (refusal on master verbatim; pass on task branch) | Delivered | TASK-140 Implementation Notes lines 51-71 — three-setup table (`master` → REFUSE, `task-99-foo` → PROCEED, `detached` → REFUSE) with reproducible invocation |

## Scope Cut Violations

Checked each item from the brainstorm's "Scope cuts" + "Out of scope, final, locked" against the cumulative diff:

- Replacing master-branch-guard entirely — Not done. Compliant.
- Extending guard to non-master branches — Not done. Compliant.
- Positive-allowlist architecture — Not done. Compliant.
- Auto-cleaning accidentally committed `.obsidian/workspace.json` — Not done. Compliant.
- Hook performance optimization — Not done. Compliant.
- `.history/` exempt — Not added (deferred per Q1). Compliant.
- "Upgrade-mode preflight (sibling task — see Q4)" was listed as out-of-scope for TASK-139 only; the brainstorm explicitly assigned it to a separate sibling — that sibling is TASK-140, exactly as locked. Compliant.

**None detected.**

## Drift List

Cumulative scope of the diff:

- `.claude/hooks/master-branch-guard.sh` — serves Q1, TASK-139 AC #1, #2.
- `skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` — serves TASK-139 AC #3 (R11 mirror).
- `skills/ralph-init/SKILL.md` — serves Q2, Q3 (TASK-139 AC #4, #5) and Q4 (TASK-140 AC #1–#4).
- `tests/unit/pretools-hooks.bats` — serves TASK-139 AC #6, #7.
- `design/ralph-init-hook-ordering-brainstorm.md` — the design input artifact itself.
- `design/ralph-init-hook-ordering-review-2026-06-13.md` — prior-round review artifact (out of feature scope; treated as meta).
- `backlog/tasks/task-139 ...md` and `task-140 ...md` — task lifecycle artifacts.

The housekeeping commit `fd06ec0` flips only TASK-140's frontmatter `status` / `updated_date` fields (2 lines), no implementation impact. Per the request brief, treated as metadata not feature content.

**No drift detected.** Every hunk traces to a Q-lock, an AC, or a lifecycle/meta artifact.

## Reviewer Notes

1. **Round-1 hook-revert recurrence — RESOLVED, no third recurrence.** The cross-check `diff <(git show HEAD:.claude/hooks/master-branch-guard.sh) .claude/hooks/master-branch-guard.sh` produces no output: the live working-tree hook matches HEAD with the full six-dir exempt set. The pattern the round-1 reviewer flagged (and resolved with `git restore`) has not recurred under TASK-140, and TASK-140 did not touch any hook files. The recurrence chain seems broken for now — no new evidence pointing to a systemic source. If it returns after a future merge, that would be the moment to file a chore to investigate.

2. **U1.5 / U1.6 numbering integrity.** Confirmed by exhaustive `grep -n "U1\.5\|U1\.6"`: only four occurrences in the file — the new section header at line 396, two body references at lines 406 and 419 (both pointing to U1.6 correctly), and the renamed section header at line 425. No orphaned "U1.5: Legacy" references survived the rename. No external file (backlog, brainstorm, tests) references `U1.5` or `U1.6` as section anchors that could break.

3. **TASK-139 changes preserved under TASK-140.** TASK-140's edits to `SKILL.md` are confined to the upgrade-mode block (lines 393-425). TASK-139's Step 3.7a split (line 173) and Step 3.11 hook-activation step (line 319) are untouched by `68c4bf2`. The two tasks compose without interference.

4. **Detached-HEAD detection is correct.** `git rev-parse --abbrev-ref HEAD` does return the literal string `HEAD` when the working tree is detached. The SKILL.md text at line 406 calls this out inline ("`HEAD` (the latter indicates detached HEAD)") so a reader doesn't have to know the git quirk. AC #2 satisfied. Smoke verification table in TASK-140 notes confirms behavior in all three setups.

5. **Refusal message quality.** The U1.5 refusal block (SKILL.md:409-418) names the problem (root-level file overwrites), the constraint (master-branch-guard denies these), the concrete recovery command (`git checkout -b task-<id>-ralph-upgrade master`), the re-invoke instruction, and the rationale back-pointer (brainstorm Q4). Every brainstorm-listed element of a "clear, recoverable message" is present.

6. **TASK-140 smoke-test process observation (not a feature defect).** Per the brief, the phantom commit `c4a366a` in TASK-140's Implementation Notes (line 41) was a smoke-test mishap: the scratch `git init` failed under the sandbox, and a subsequent `git -C "$SMOKE" commit` walked up to the main repo, creating an empty commit on the wrong tree. `git cat-file -e c4a366a` returns false at HEAD, confirming the recovery succeeded — the phantom is unreachable from any ref. The real implementation commit is `68c4bf2`, which is correctly attested elsewhere in the notes. Suggestion for future smoke patterns: prefer `git init -q -b master "$SMOKE" || exit 1` followed by `git -C "$SMOKE" rev-parse --git-dir` as a sanity gate before any `git -C "$SMOKE" commit`, so a failed init becomes a loud test failure instead of a silent main-repo write. Not blocking the feature.

7. **Housekeeping commit `fd06ec0` is benign.** Flips TASK-140 status from `In Progress` to `Done` and bumps `updated_date`. No code, no doc, no test change. The root cause of the original dropped status-flip is unknown per the brief; logging an investigation chore would be defensible if it recurs on TASK-141. Single occurrence is not yet a pattern.

8. **Feature complete.** All five brainstorm Q-locks (Q1, Q2, Q3, Q4, Q5) plus all 13 ACs across both sibling tasks have evidence of delivery. The Aligned verdict from round 1 stands, and TASK-140 lands the Q4 sibling exactly per its lock. The feature can be closed; future master-branch self-blocks in either init flow or upgrade flow are now prevented by two independent mechanisms (reorder + widen) plus a third for the upgrade-specific case (preflight refusal).
