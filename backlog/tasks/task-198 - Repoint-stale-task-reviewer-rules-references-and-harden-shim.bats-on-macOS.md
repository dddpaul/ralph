---
id: TASK-198
title: Repoint stale task-reviewer-rules references and harden shim.bats on macOS
status: Done
assignee: []
created_date: '2026-07-04 06:23'
updated_date: '2026-07-04 08:01'
labels:
  - 'feature:ralph-marketplace'
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up from the ralph-marketplace feature review (design/ralph-marketplace-review-2026-07-04.md, Verdict: Aligned). Two non-blocking hygiene items the cumulative review surfaced, both outside the in-scope ACs of TASK-187..197.

Item 1 — stale references in .claude/task-reviewer-rules.md. TASK-195 correctly repointed only the R11 parity table to plugins/ralph/skills/ralph-init/templates/... The R16 section and the header/loading narrative (around lines 3, 186, 206) still name top-level agents/ and skills/ paths. Repoint those to plugins/ralph/agents/... and plugins/ralph/skills/... Leave the R11 table as-is (already correct). Verify grep-clean with:

```
grep -nE "(^|[^a-zA-Z/])(agents|skills)/ralph" .claude/task-reviewer-rules.md
grep -nE "agents/(task-reviewer|ralph-reviewer)[.]md" .claude/task-reviewer-rules.md
```

After the fix these should match only plugins/ralph/... forms.

Item 2 — shim.bats resolver tier-2 false-fails on macOS. setup_test_dir uses mktemp under /var/folders/... which is a symlink to /private/var/... The shim sets RALPH_PROJECT_ROOT via pwd -P (canonical /private/var/...), while the test builds the expected orchestrator path from the non-canonical /var/... mktemp path, so the tier-2 expected-vs-actual comparison mismatches. Tiers 4/5 and the byte-identity test pass; this is a test-harness canonicalization nit, not a resolver defect. Fix by canonicalizing the temp dir in tests/helpers/common.bash setup_test_dir, e.g.:

```
TEST_DIR="$(cd "$(mktemp -d)" && pwd -P)"
```

so the expected path matches the shim canonicalized RALPH_PROJECT_ROOT on macOS and Linux.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 R16 and header/loading-narrative path references in .claude/task-reviewer-rules.md are repointed from top-level agents/ and skills/ to plugins/ralph/agents/ and plugins/ralph/skills/
- [x] #2 grep confirms no stale top-level agents/ or skills/ralph file-path references remain in .claude/task-reviewer-rules.md, and the R11 parity table still points at plugins/ralph/skills/ralph-init/templates/
- [x] #3 tests/helpers/common.bash canonicalizes the test temp dir with pwd -P or realpath so shim.bats resolver tier-2 no longer false-fails on macOS
- [ ] #4 Full bats suite passes on macOS (bats tests/)
- [x] #5 uv run pytest passes
- [x] #6 uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan (autonomous): Item 1 — repoint 3 LIVE pointer refs in .claude/task-reviewer-rules.md: line 3 header (agents/task-reviewer.md → plugins/ralph/agents/task-reviewer.md, keep ~/.claude/ fallback), line 186 R16 consumer (skills/ralph-task/SKILL.md → plugins/ralph/skills/ralph-task/SKILL.md), line 206 R16 mirror-note (skills/ralph-init/templates/claude/task-reviewer-rules.md → plugins/ralph/skills/...). Leave R11 table (already correct) and R14 line 165 (accurate TASK-92 history: git log 3dc64fd shows .claude/agents→agents/ top-level move; TASK-188 4c89342 later moved to plugins/ralph — repointing 165 would falsify history and is outside AC#1 scope). Item 2 — canonicalize temp dir in tests/helpers/common.bash setup_test_dir: TEST_DIR=$(cd $(mktemp -d) && pwd -P) so shim.bats tier-2 expected path matches shim RALPH_PROJECT_ROOT (pwd -P, ralph.sh:11). No-op on Linux (mktemp not symlinked here), fixes macOS /var→/private/var. Verify: 2 greps clean of bare top-level live pointers, R11 table intact, bats tests/ + uv run pytest + uv run ruff check .

Commit: `0a7420f` - task-198: Repoint task-reviewer-rules refs to plugins/ralph and canonicalize test temp dir (pwd -P) for macOS shim.bats

Results (commit 0a7420f): AC#1 DONE (lines 3/186/206 repointed to plugins/ralph/agents & plugins/ralph/skills; verified). AC#2 DONE — grep 'agents|skills)/ralph' clean; grep 'agents/(task-reviewer|ralph-reviewer).md' now matches only line 3 (plugins/ralph + ~/.claude fallback) and line 165 (R14 TASK-92 historical git-mv narrative, accurate per git 3dc64fd, out of scope — NOT a stale live pointer); R11 table intact (12 plugins/ralph/skills/ralph-init/templates refs). AC#3 DONE (setup_test_dir canonicalizes via pwd -P). AC#5 DONE (uv run pytest: 185 passed). AC#6 DONE (uv run ruff check .: All checks passed).

AC#4 DEFERRED (cannot verify full-suite green — pre-existing, out-of-scope breakage). shim.bats (the file this task fixes) passes 4/4 incl. resolver tier-2. BUT the full bats suite has 71 pre-existing failures IDENTICAL on clean master (stash-and-rerun baseline: 108 ok / 71 not ok both with and without this diff), so this change causes ZERO regression. Root cause: common.bash line 10 RALPH_SCRIPT='$PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts/ralph.sh' points at a file that is NOT tracked in git (git log for it is empty; only tracked ralph.sh are the two thin shims). task-188 (4c89342, ralph-marketplace relocation) repointed RALPH_SCRIPT there without a sourceable bash ralph.sh existing — the arg-parsing logic moved to the Python orchestrator (ralph_orchestrator.py, 185 pytest tests green) but the bash unit/integration .bats still 'source $RALPH_SCRIPT' and fail 'No such file or directory'. Fixing that is a separate task (restore/port the sourced surface or repoint+rewrite the bash tests) — outside TASK-198's non-blocking-hygiene scope and the autonomous one-task rule. Follow-up task to be filed. My setup_test_dir fix is a Linux no-op (mktemp -d not symlinked here; verified raw==pwd -P) and correctly canonicalizes /var->/private/var on macOS.

Done: task-reviewer APPROVED. Reviewer independently reproduced the 108 ok / 71 not ok baseline on BOTH the branch and clean master (identical failing-test sets → zero regression), confirmed R5 portability (cd/mktemp -d/pwd -P), R14 line-165 historical preservation (git-verified), R12 line-206 intentional-absence, and validated the AC#4 deferral. AC#1/2/3/5/6 met; AC#4 deferred (pre-existing, out-of-scope RALPH_SCRIPT breakage from task-188 — a follow-up task should restore/port the sourced bash surface or repoint+rewrite the bash tests). shim.bats 4/4, pytest 185 passed, ruff clean.

AC#4 deferral follow-up filed: TASK-199 (Fix orphaned RALPH_SCRIPT — 71 bash tests source an untracked ralph.sh). Tracks the pre-existing full-bats-suite breakage that blocks AC#4; out of scope for this task.
<!-- SECTION:NOTES:END -->
