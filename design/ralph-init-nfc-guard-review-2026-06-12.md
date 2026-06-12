# Feature Review: ralph-init Unicode NFC normalization guard (TASK-136)

**Verdict: Aligned**

**Passes run:** 1 (PRD/intent coverage via handoff source), 2 (Non-Goal Protection vs "Out of scope"), 5 (Out-of-Scope Creep)
**Passes skipped:** 3 (no brainstorm doc — handoff task), 4 (no PRD "Success Metrics" section — handoff task uses ACs as success criteria, already covered by Pass 1)

Authoritative intent = the inbound handoff task description (no PRD, no brainstorm). Diff range: `8f4c89c..HEAD` (4 files, 19 KB, 315 lines). Three commits: `1f42d7c` (impl), `8db61ab` (Done), `07404dc` (merge).

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| AC-1 | `templates/git-hooks/pre-commit` exists, executable, bash shebang | Delivered | New file at diff:143-148, `new file mode 100755`, `#!/bin/bash` at line 149 |
| AC-2 | `bash -n` clean | Delivered | Hook is short, structured, no syntax irregularities; orchestrator + task-reviewer APPROVED confirms |
| AC-3 | Positive regression test (clean unrelated path passes) | Delivered | `tests/unit/pre-commit-hook.bats:250-260` "passes when staging an unrelated clean path" |
| AC-4 | Negative test: HEAD=NFC, stage NFD → exit 1 + BLOCKED on stderr | Delivered | `tests/unit/pre-commit-hook.bats:262-273` asserts `status -eq 1` and `BLOCKED` in output; hook writes diagnostic to `>&2` at line 206 |
| AC-5 | Inverse negative: HEAD=NFD, stage NFC → exit 1 + BLOCKED | Delivered | `tests/unit/pre-commit-hook.bats:275-286` symmetric assertion |
| AC-6 | SKILL.md instructs `git config --local core.precomposeunicode true` during init | Delivered | SKILL.md Step 3.3, diff line 70: code block contains the exact command, framed as bootstrap |
| AC-7 | SKILL.md U2 status table lists `templates/git-hooks/pre-commit` with comparison semantics | Delivered | Diff line 98: row 5 — "exact content match against `templates/git-hooks/pre-commit` (Unicode NFC/NFD duplicate guard, see TASK-136)"; table renumbered 5→13 coherently |
| AC-8 | Pre-existing tests still pass | Delivered | Implementation notes document 6/6 new-test pass; two pre-existing failures (`on-error-continue.bats:17`, `timeout-handling.bats:10`) verified unchanged on master — not introduced by this diff |
| AC-9 | Live `.git/hooks/pre-commit` matches template byte-for-byte and is executable (R11 mirror) | Delivered | Orchestrator pre-check confirmed `diff` produced no output and file is executable |

**Defense mechanism examination (Scope-section behavior):** The hook script (`skills/ralph-init/templates/git-hooks/pre-commit` lines 166-210) correctly implements the spec:
- Pulls staged paths via `git -c core.quotePath=false diff --cached --name-only` (correct: raw UTF-8 bytes, not C-escapes)
- Builds NFC index from `git ls-tree -r HEAD --name-only`
- Normalizer prefers `iconv -f utf-8-mac -t utf-8` (BSD/macOS), falls back to `python3 -c 'unicodedata.normalize("NFC", …)'` — matches the scope's exact prescription
- Reports BLOCKED on stderr, exits 1
- Empty HEAD (`|| exit 0`) and empty stage (`[ -z "$staged" ] && exit 0`) gracefully bypass — covered by the two edge tests at bats lines 288-303
- Same-path modifications pass (`if [ "$e" != "$p" ]` — byte equality bypasses the warning) — covered by bats lines 305-314

## Non-Goal Violations

Verified against the four "Out of scope" items in the task body:

| Out-of-scope item | Status |
|---|---|
| Backporting into already-initialized downstream projects | Respected — diff only touches `skills/ralph-init/` templates + this repo's own R11-mirror live hook; the upgrade flow (U2/U3/U4) is the prescribed pull path, not a push |
| Adding a Claude PreToolUse guard under `.claude/hooks/` | Respected — no `.claude/hooks/` files added or modified in diff |
| Auto-fixing NFD paths in-place (renaming) | Respected — hook script lines 205-210 only `echo` diagnostic + `exit 1`, no `git mv` or rename anywhere |
| Cleaning the downstream `reestr.digital.gov.ru` tree | Respected — no cross-repo writes (and would be impossible from this diff) |

None detected.

## Scope Cut Compliance

The "Out of scope" enumeration above doubles as the task's scope-cut list. All four cuts respected.

## Drift List

No drift detected. Every hunk in the diff maps cleanly to an in-scope AC:
- task-136 backlog file: AC status flips + Implementation Notes (lifecycle)
- `skills/ralph-init/SKILL.md` Step 3.3 + Step 4 file-list + U2 table + U3 example + U4 apply + U5 success-display: AC-6, AC-7, plus the natural propagation of "new managed file" into every place the upgrade flow lists managed files (defensible — keeping U2 list and U3/U4/U5 in sync is a single coherent edit, not creep)
- `templates/git-hooks/pre-commit` (new): AC-1, AC-2, plus the defense behavior
- `tests/unit/pre-commit-hook.bats` (new): AC-3, AC-4, AC-5, plus three defensive edge tests (empty repo, empty stage, modification-passes) which strengthen the guard without expanding scope

## Reviewer Notes

Non-blocking observations:

1. **Belt-and-suspenders framing is well-justified.** The SKILL.md prose at diff line 73 ("the config catches new files written via macOS, the hook catches NFD bytes that slip in via patch import, `git mv`, or a foreign filesystem") correctly characterizes why both fixes ship together rather than one alone. This addresses the root cause (#1 missing `core.precomposeunicode`, #2 missing pre-commit guard) symmetrically.

2. **Test fixture is platform-aware.** `tests/unit/pre-commit-hook.bats:241` sets `core.precomposeunicode false` so the test harness can stage true NFD bytes on macOS (which would otherwise pre-compose them at the git layer and defeat the test). This is the right call; it also serves as documentation of how the production setting (`true`) interacts with the hook.

3. **U2 table renumbering (5→13) is mechanical but invasive.** The diff renumbers 8 list items to insert one. No content was lost; the order is correct (pre-commit grouped with the other two hooks). Worth noting only because future template additions will require similar renumbering — a numbered Markdown list could be considered if this happens again, but that's a style preference, not a defect.

4. **Hook diagnostic is actionable.** The message at hook lines 206-208 names the violating pair AND offers a remediation (`git mv` or `git rm --cached`). Better than the example diagnostic in the task description, which only described the problem.

5. **Edge cases beyond ACs.** Three extra bats tests (empty repo, empty stage, modification-passes) are added without being mandated by the ACs. These are defensive-test discipline — they pin down behaviors a future refactor might break. Not creep; valid hardening.

6. **Same-blob NFC+NFD pair already in HEAD (not staged) is not detected.** The hook only checks staged paths against HEAD — not HEAD-internal duplicates. This is correct for the stated intent (prevent introducing a duplicate) but means a project that already contains the defect would not see the hook fire until someone tried to stage a touching change. Acceptable: scope explicitly excludes "Cleaning the downstream reestr.digital.gov.ru tree" — that's TASK-2 in the downstream project.

7. **R11 mirror discipline maintained.** AC-9 (mirror to live `.git/hooks/pre-commit`) follows the same pattern as commit-msg (TASK-134) and post-commit. The orchestrator pre-check confirmed parity. Consistent with project conventions.
