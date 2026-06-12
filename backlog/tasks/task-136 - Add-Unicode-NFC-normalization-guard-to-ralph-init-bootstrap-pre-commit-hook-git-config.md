---
id: TASK-136
title: >-
  Add Unicode NFC normalization guard to ralph-init bootstrap (pre-commit hook +
  git config)
status: Done
assignee: []
created_date: '2026-06-12 08:42'
updated_date: '2026-06-12 14:29'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

A downstream Ralph project (reestr.digital.gov.ru) accumulated 4 NFD-duplicate paths in its git tree after Ralph autonomously committed source files whose names were synthesized in NFD while the NFC originals were already on master. macOS APFS collapses both into one working-tree file, hiding the defect, but `git ls-tree -r HEAD` shows two entries with the same display name → broken checkout on case/Unicode-strict filesystems (Linux, Windows), and broken citations in any downstream document that referenced the NFC form.

Root cause is twofold:
1. `/ralph-init` does not set `core.precomposeunicode true`, so git's working-tree to tree pipeline keeps whatever encoding the filesystem hands back.
2. There is no pre-commit hook that rejects an NFD path when an NFC counterpart already exists in the tree (or vice-versa).

Found by the task-reviewer agent on TASK-1 of the reestr.digital.gov.ru project. The downstream defect cleanup is handled there (a separate local TASK-2 in that project). This handoff fixes the bootstrap so the defect cannot recur in any project initialized or upgraded with /ralph-init.

## Reproducer

In the downstream project, run:

```bash
git ls-tree -r HEAD | awk '{print $4}' | LC_ALL=C sort | uniq -d
```

Pre-cleanup output (4 lines):

```
source/RITTM - Регистрация ПО в Реестре российского программного обеспечения.md
source/attachments-3455866639/4. Форма_Проверка сторонних лицензий.docx
source/attachments-3455866639/5. Форма_Жизненный цикл ПО.docx
source/attachments-3455866639/7. Письмо об удаленной демонстрации тестового экземпляра ПО для комиссиии Минцифры.docx
```

With the proposed pre-commit guard installed BEFORE task-1 was committed, the second add of each path (NFD variant of an existing NFC path) would have been blocked with a diagnostic like:

```
BLOCKED: staged path "X" duplicates existing tree path under a different Unicode normalization (NFD vs NFC). Use git mv or re-add with `iconv -f utf-8-mac -t utf-8` to normalize.
```

## Scope

In scope:
- New git hook `skills/ralph-init/templates/git-hooks/pre-commit` (pure bash, match style of templates/git-hooks/commit-msg)
- Pre-commit logic: for each path returned by `git diff --cached --name-only`, check whether (a) the staged path is NFD and an NFC counterpart already exists in `git ls-tree -r HEAD --name-only`, or (b) the inverse. If yes, exit 1 with a clear diagnostic. Use `iconv -f utf-8-mac -t utf-8` for NFD to NFC conversion (BSD iconv on macOS) with a `python3 -c 'import unicodedata...'` fallback for portability.
- Patch `skills/ralph-init/SKILL.md`: add `git config --local core.precomposeunicode true` to whichever step owns git-config bootstrap (Step 1 preflight or new Step 3.x), so newly-initialized projects auto-normalize working-tree to tree.
- Add the new pre-commit hook to the `/ralph-init upgrade` flow status table (U2) with correct comparison semantics.
- Regression tests under tests/ following TASK-134 convention: (a) positive — staging a clean unrelated path passes; (b) negative-NFD — staging an NFD variant of an existing NFC path is rejected; (c) negative-NFC — inverse direction also rejected.

Out of scope:
- Backporting into already-initialized downstream projects — those carry their own .git/hooks/ copies and will pull the new hook via `/ralph-init upgrade`.
- Adding a Claude PreToolUse guard under `.claude/hooks/`. The git pre-commit layer is the right one; PreToolUse cannot see staged files.
- Auto-fixing NFD paths in-place (renaming). The hook only rejects; the human resolves.
- Cleaning the downstream reestr.digital.gov.ru tree (handled in its own TASK-2).

## Files

- `skills/ralph-init/SKILL.md` (exists) — add precomposeunicode bootstrap step + new file row in upgrade U2 status table
- `skills/ralph-init/templates/git-hooks/commit-msg` (exists) — read-only here, reference for hook style; do not modify
- `skills/ralph-init/templates/git-hooks/post-commit` (exists) — read-only, reference for style; do not modify
- `skills/ralph-init/templates/git-hooks/pre-commit` (NEW) — the new normalization-check hook
- `tests/` (exists) — add positive + 2 negative regression tests following the TASK-134 fixture convention

## Source

Source: /Users/paul/Private/Alfa/Projects/reestr.digital.gov.ru@7e526b6

Reproducer evidence: `git ls-tree -r 7e526b6` in that project shows 4 duplicate display-name entries — same blob hash, different path bytes. Verified via hex inspection: NFC form has `d0b9` (й = U+0439) where NFD form has `d0b8 cc86` (и + combining breve U+0306).

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, hook exit code, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. The "Out of scope" items will not be accidentally pulled in by ambiguous ACs.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/templates/git-hooks/pre-commit exists, is executable, and starts with the bash shebang
- [x] #2 bash -n on skills/ralph-init/templates/git-hooks/pre-commit exits 0
- [x] #3 New positive regression test under tests/ stages a clean unrelated path, runs the pre-commit hook against the fixture, and the hook exits 0
- [x] #4 New negative regression test under tests/ simulates HEAD containing an NFC path, stages an NFD form of the same path, runs the pre-commit hook, and the hook exits 1 with BLOCKED diagnostic on stderr
- [x] #5 Inverse-direction negative test: HEAD has NFD path, stages NFC variant, hook exits 1 with BLOCKED diagnostic
- [x] #6 skills/ralph-init/SKILL.md grep matches an instruction to run git config --local core.precomposeunicode true during init
- [x] #7 skills/ralph-init/SKILL.md upgrade-flow U2 status table lists templates/git-hooks/pre-commit with comparison semantics
- [x] #8 All pre-existing tests under tests/ still pass after the change (run the project test suite, exit 0)
- [x] #9 Live .git/hooks/pre-commit in this repo matches skills/ralph-init/templates/git-hooks/pre-commit byte-for-byte (R11 mirror, parallel to commit-msg and post-commit) and is executable
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Author skills/ralph-init/templates/git-hooks/pre-commit (NFC/NFD duplicate guard, iconv-utf8-mac with python3 fallback, core.quotePath=false so raw bytes compare). 2) Patch skills/ralph-init/SKILL.md: Step 3.3 writes the hook + sets core.precomposeunicode true; U2 status table adds the pre-commit row at position 5 (renumbered 5-13); U3 status display, U4 apply, Step 4 summary all updated. 3) Mirror to live .git/hooks/pre-commit byte-for-byte (R11). 4) Add tests/unit/pre-commit-hook.bats with positive + 2 negative (NFD→NFC HEAD, NFC→NFD HEAD) + empty-repo + empty-stage + modification-passes.

Test suite: tests/unit/pre-commit-hook.bats — 6/6 ok (positive + NFD→NFC negative + NFC→NFD negative + 3 edge cases). Full suite has one pre-existing failure in tests/integration/on-error-continue.bats:17 (FAILED_ITERATIONS Python parse) that reproduces verbatim on master (diff master..HEAD on that file is empty) — unrelated to TASK-136 scope.

Commit: `1f42d7c` - task-136: Add Unicode NFC normalization guard to ralph-init bootstrap

task-reviewer APPROVED (verdict above). Reviewer also flagged a second pre-existing failure in tests/integration/timeout-handling.bats:10 (Temp file cleanup on timeout) — git diff master..HEAD on that file is also empty, so unrelated to TASK-136. Both pre-existing failures are out of this task's scope.
<!-- SECTION:NOTES:END -->
