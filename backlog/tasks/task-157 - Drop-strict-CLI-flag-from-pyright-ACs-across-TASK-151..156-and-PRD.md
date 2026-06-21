---
id: TASK-157
title: Drop --strict CLI flag from pyright ACs across TASK-151..156 and PRD
status: Done
assignee: []
created_date: '2026-06-21 14:00'
updated_date: '2026-06-21 14:19'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Pyright 1.1.410 (and any version >=1.1.350) removed `--strict` as a CLI flag — strict mode is now config-driven. pyproject.toml correctly sets `[tool.pyright].strict = ["skills/ralph-run/scripts"]`, so the right invocation is plain `uv run pyright skills/ralph-run/scripts`. The merged TASK-150 code is fine; only the AC TEXT in the remaining tasks (and the PRD they derive from) needs the literal substring `pyright --strict` shortened to `pyright`.

Discovered during post-merge sanity check on master after TASK-150: `uv run pyright --strict skills/ralph-run/scripts` returns `Unexpected option --strict` exit 1. ruff and pytest pass. Strict mode IS enforced via [tool.pyright].strict in pyproject.toml.

Affected files (all in-line substring replacements; no AC count change, no frontmatter change, no section marker touch):
- `backlog/tasks/task-151 - Port-preflight-wait-heartbeat-and-usage-check-helpers-from-bash-to-Python.md`
- `backlog/tasks/task-152 - Port-signals-tasks-heartbeat-usage-wrapper-and-Tool-ABC-modules.md`
- `backlog/tasks/task-153 - Implement-claude-code-subprocess-with-tee-timeout-and-process-group-cleanup.md`
- `backlog/tasks/task-154 - Wire-orchestrator-entry-point-opencode-subprocess-and-fake-claude-E2E-test.md`
- `backlog/tasks/task-155 - Wire-RALPH_IMPL-dispatch-in-outer-shim-and-mirror-to-ralph-init-templates.md`
- `backlog/tasks/task-156 - Cutover-to-Python-orchestrator-delete-bash-document-downstream-upgrade-path.md`
- `design/ralph-python-refactor-prd.md`

Replacement: `uv run pyright --strict skills/ralph-run/scripts` → `uv run pyright skills/ralph-run/scripts` (per-file; the rest of the AC line stays identical).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All 6 task files (TASK-151 through TASK-156) have `pyright --strict` replaced by `pyright` in their pyright AC line
- [x] #2 design/ralph-python-refactor-prd.md has the same replacement applied wherever the literal `pyright --strict` appears
- [x] #3 AC line count on each of TASK-151..156 is unchanged from before the edit (verify with backlog task view)
- [x] #4 `uv run pyright skills/ralph-run/scripts` (no --strict) passes on master HEAD before merge — confirms the corrected command actually works
- [x] #5 After edits, `grep -rEh 'pyright --strict' backlog/tasks/task-15[1-6]*.md design/ralph-python-refactor-prd.md` returns zero matches (TASK-157 itself intentionally quotes the literal as part of its description and is excluded; brainstorm is historical and out of scope)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Substring replacement applied to 7 spec-surface files (6 task files + PRD) and bonus to backlog/docs/doc-2 (overview doc carried the same misspecification; out of strict reading of AC #2 but in the spirit of TASK-157).

Verification:
- Scoped grep 'pyright --strict' across backlog/tasks/task-15[1-6]*.md + design/ralph-python-refactor-prd.md + backlog/docs/doc-2*.md → 0 hits
- AC line counts unchanged: TASK-151=9, TASK-152=10, TASK-153=11, TASK-154=12, TASK-155=10, TASK-156=12 (matches pre-edit counts from TASK-148 fan-out verification)
- 'uv run pyright skills/ralph-run/scripts' on master HEAD: warning about requires-python (cosmetic, see PRD constraint), then '0 errors, 0 warnings, 0 informations' — the corrected command works.

Out-of-scope (intentionally NOT changed):
- backlog/.ralph-run.log — ephemeral runtime log; Ralph quoted the bug in its own task-summary narration; log files regenerate per run.
- backlog/tasks/task-157 — this wrapper task intentionally quotes the literal in its description.
- backlog/tasks/task-150 — Done and merged; touching its checked-off AC text would be revisionism; plan/notes already explain the discrepancy.
- design/ralph-python-refactor-brainstorm.md — brainstorm is frozen human-design history per R16 spirit.

Commit: `9cc29c5` - task-157: Drop --strict CLI flag from pyright ACs

task-reviewer APPROVED after one round of CHANGES REQUESTED.

Round 1 (agentId ac8f8e422e817143a): doc-2 line 27 botched substitution — I expanded `pyright --strict` to a parenthetical instead of trimming, breaking the in-backtick CLI literal on a line with two occurrences. Fixed in commit 90025ed by applying the trim-only rule.

Round 2 (agentId a8fd735df00a404bd): confirmed clean. Doc-2 line 27 now mirrors the Lint line on line 26 in style. Scoped grep returns 0 across all 8 spec-surface files (6 task files + PRD + doc-2). No collateral, no Python code touched, AC line counts unchanged, pyright on HEAD reports 0 errors.
<!-- SECTION:NOTES:END -->
