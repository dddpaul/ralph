# Feature Review: ralph-init-hook-ordering (2026-06-13)

**Verdict: Aligned**

**Passes run:** 1 (Intent → Implementation matrix against brainstorm), 3 (Scope Cuts), 5 (Out-of-Scope Creep)
**Passes skipped:** 2 (no PRD, so no "Non-Goals" section per se — though the brainstorm's "Scope cuts" subsection covers equivalent ground and is checked under Pass 3), 4 (no PRD → no Success Metrics section)

Authoritative intent = `design/ralph-init-hook-ordering-brainstorm.md` (Q1–Q5 locked decisions in the 2026-06-13 addendum + 8 ACs in the Phase 4 sketch). No PRD exists for this feature.

Diff range: `a968a70..HEAD` (3 commits: implementation + Done + merge; 6 files; 338 insertions, 4 deletions).

## Intent → Implementation Matrix

The brainstorm addendum locks five decisions (Q1–Q5) plus eight ACs. Treating each as an intent unit:

| ID | Intent (brainstorm / AC) | Status | Evidence |
|----|----|----|----|
| Q1 | Six exempt dirs: `.obsidian/`, `.vscode/`, `.idea/`, `.cursor/`, `.zed/`, `.fleet/`, each in both `*/<dir>/*` and `<dir>/*` shapes; skip `.history/` | Delivered | `.claude/hooks/master-branch-guard.sh:32-37` (committed at HEAD) — six new `case` lines, exact shape parity with the existing `.claude/` / `design/` exemptions; `.history/` not added |
| Q2 | Move only `.claude/settings.json` to the very end (after Step 3.10), establishing "hook activation is the last act of init" | Delivered | `skills/ralph-init/SKILL.md:319-322` — new Step 3.11 placed after 3.10; rationale paragraph states the invariant explicitly |
| Q3 | Split Step 3.7a: `.claude/hooks/*.sh` + `.claude/settings.local.json` stay early, only `.claude/settings.json` defers; no placeholder/overwrite dance | Delivered | `SKILL.md:173-177` — Step 3.7a title rewritten, settings.json line removed; explanatory paragraph at line 177 ties the deferred half to Step 3.11 |
| Q4 | Upgrade-mode follow-up is a separate sibling task, NOT bundled here | Delivered (by absence) | Diff contains no `U4` / upgrade-mode edits. Task body confirms the sibling is filed separately |
| Q5 | Option D (gitignore-aware hook) rejected; explicit six-dir list only | Delivered (by absence) | No `.gitignore`-reading logic added to the hook; only literal `case` patterns |
| AC #1 | Exempt block widens to six dirs in both shapes | Delivered | `.claude/hooks/master-branch-guard.sh:32-37` |
| AC #2 | Header comment (lines 2-3) enumerates the new exempts | Delivered | Header now reads `(except .claude/, design/, .obsidian/, .vscode/, .idea/, .cursor/, .zed/, .fleet/, .gitignore)` — all nine listed |
| AC #3 | Template at `skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` byte-identical to live (R11) | Delivered at commit | `git show HEAD:skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` matches `git show HEAD:.claude/hooks/master-branch-guard.sh`. See Reviewer Note 1 for a working-tree drift observed today |
| AC #4 | Step 3.7a split: hooks + settings.local.json stay; settings.json removed | Delivered | `SKILL.md:173-177` |
| AC #5 | New Step 3.11 after 3.10 writes `.claude/settings.json` from template; body has rationale + brainstorm back-pointer | Delivered | `SKILL.md:319-322` — rationale present, back-pointer `design/ralph-init-hook-ordering-brainstorm.md` cited verbatim |
| AC #6 | Six new positive-case tests, one per new exempt dir | Delivered | `tests/unit/pretools-hooks.bats:143-182` — six `@test` blocks, each named for one of the six dirs |
| AC #7 | Existing exempt tests (`.claude/`, `.gitignore`, task branch, detached HEAD) and deny case continue to pass | Delivered | Full suite run: 31/31 pass |
| AC #8 | Smoke verification on a scratch repo documented in Implementation Notes | Delivered | Task body documents the three Step 3.9 paths piped into the hook, all returning exit 0, plus a deny-path sanity check |

## Scope Cut Violations (brainstorm "Scope cuts" + "Out of scope, final, locked")

Checked each cut against the diff:

- Replacing master-branch-guard entirely — Not done. Compliant.
- Extending guard to non-master branches — Not done. Compliant.
- Positive allowlist architecture — Not done. Compliant.
- Auto-cleaning accidentally committed `.obsidian/workspace.json` — Not done. Compliant.
- Hook performance optimization — Not done. Compliant.
- Upgrade-mode preflight (Q4 sibling) — Not done here, deferred to sibling task as directed. Compliant.
- `.history/` exempt — Not added (preliminary brainstorm Q1 confirms deferred). Compliant.

**None detected.**

## Drift List

Scope of diff is tightly bounded:

- `.claude/hooks/master-branch-guard.sh` — directly serves AC #1, #2, Q1.
- `skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` — directly serves AC #3.
- `skills/ralph-init/SKILL.md` — directly serves AC #4, #5, Q2, Q3.
- `tests/unit/pretools-hooks.bats` — directly serves AC #6, #7.
- `design/ralph-init-hook-ordering-brainstorm.md` (new) — brainstorm artifact, explicitly authored as the design input for this feature.
- `backlog/tasks/task-139*.md` — task lifecycle artifact.

**No drift detected.** Every hunk traces to an AC, a locked Q-decision, or a lifecycle/meta artifact.

## Reviewer Notes

1. **Working-tree drift on live hook (outside review scope, but flag-worthy).** The cumulative diff against HEAD is clean and correct, but the live file `.claude/hooks/master-branch-guard.sh` is currently dirty in the working tree (`git status` shows ` M`). The working copy has reverted to the pre-feature header and lacks the six new `case` lines, while `git show HEAD:.claude/hooks/master-branch-guard.sh` retains them. This is the **second recurrence** of the same pattern observed after TASK-137 merged (the user resolved that one with `git checkout .`). This is post-merge tampering or an unintentional checkout, not a feature defect — but it does mean Claude Code is loading the *old* hook from disk right now, so the new six-dir exempts are not actually active until the working tree is restored. Worth running `git restore .claude/hooks/master-branch-guard.sh` to re-sync with HEAD, or filing a chore task to investigate the source of the drift (some process in the Ralph loop or devcontainer mount may be touching this file after the merge).

2. **Invariant durability.** Step 3.11's body explicitly names the invariant ("hook activation is the last act of init") in bold and back-points to the brainstorm. That phrasing should survive future SKILL.md edits — good. If you ever add a Step 3.12 template write, the invariant says: insert *above* 3.11, never below. Consider a one-line guard comment near the top of Step 3 that restates the invariant, as a future-proofing nudge.

3. **Test surface tight to spec.** The six new bats tests each exercise only `Edit` against a representative path in the dir. The hook's `Write` branch and the `*/<dir>/*` shape (absolute path containing the dir as a non-leading segment) are not separately covered, but they reuse the same `case` arm. Low risk; calling it out only because it's the one place test coverage could grow without adding scope.

4. **Brainstorm hand-off quality.** Q1–Q5 lockfile + Phase 4 sketch in the brainstorm addendum mapped 1:1 onto the eight ACs with no ambiguity. The implementation traceback was easy precisely because the brainstorm did the work upfront. This is a clean example of the design → task pipeline behaving as intended.

5. **Sibling-task referent.** The brainstorm and the task body both reference a separate upgrade-mode task per Q4. Suggest cross-linking it (`backlog task list -l feature:ralph-init-hook-ordering --plain`) so a future reviewer can confirm the family stays cohesive. Not blocking.
