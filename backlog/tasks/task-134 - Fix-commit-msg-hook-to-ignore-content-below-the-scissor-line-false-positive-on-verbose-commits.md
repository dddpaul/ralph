---
id: TASK-134
title: >-
  Fix commit-msg hook to ignore content below the scissor line (false-positive
  on verbose commits)
status: In Progress
assignee: []
created_date: '2026-06-11 17:33'
updated_date: '2026-06-11 18:04'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

A fresh Ralph project (bootstrapped via /ralph-init) cannot make its initial commit when the user has `commit.verbose=true` or invokes `git commit -av`. Git appends the full staged diff to .git/COMMIT_EDITMSG below the scissor line `# ------------------------ >8 ------------------------`. The Ralph commit-msg hook reads the entire file (the scissor section is stripped by git AFTER the hook runs), so any forbidden trailer pattern that appears inside the diff trips the guard — even when the author-written message is clean.

This is self-inflicted: templates/claude/hooks/commit-msg-guard.sh contains the literal regex `'Co-Authored-By|Generated with Claude Code'` as its own grep pattern. On the very first commit of a ralph-init scaffold, that file is in the diff, so the sibling commit-msg hook reads its own twin's grep pattern out of the diff and rejects the commit. Verified empirically in /Users/paul/Private/Alfa/Projects/reestr.digital.gov.ru today.

## Scope

In scope:
- Patch `templates/git-hooks/commit-msg` to strip the scissor section (and ideally diff/comments) before grepping. Two viable approaches: (a) `sed '/^# -\{24\} >8 -\{24\}$/,$d' "$msg_file"`; (b) `git stripspace --strip-comments < "$msg_file"`. Prefer (b) — it is the idiomatic git way and handles both comments and the scissor block in one call.
- Add a regression test under `tests/` (any tier — unit shell test or bats integration) that reproduces the scenario: a COMMIT_EDITMSG containing a clean message plus a scissor-delimited diff that includes the forbidden trailer literally; the hook must exit 0.
- Add a negative test: a COMMIT_EDITMSG whose author-written body (above the scissor) actually contains the forbidden trailer still exits 1.

Out of scope:
- Changing the forbidden-pattern list itself.
- Touching `.claude/hooks/commit-msg-guard.sh` (the PreToolUse guard — different scope, different file). Note: this same PreToolUse hook in ~/.claude also blocks Bash commands that contain the forbidden substrings literally, which made composing this handoff awkward. Possibly worth a follow-up task to scope that guard to actual commit-related commands.
- Loosening or removing the hook for verbose-commit users.
- Backporting the patched hook into already-initialized downstream projects (the user owns those .git/hooks/ copies).

## Files

- `skills/ralph-init/templates/git-hooks/commit-msg` (exists) — the hook itself; current implementation greps the whole file.
- `skills/ralph-init/templates/claude/hooks/commit-msg-guard.sh` (exists) — read-only here; this is the file whose grep pattern appears verbatim in init diffs and triggers the bug. Do not modify in this task.
- `tests/unit/` or `tests/integration/` (exists) — add the regression and negative tests here following existing conventions.
- `skills/ralph-init/SKILL.md` (exists) — only update if the upgrade-flow U2 "exact content match" comparison logic needs adjustment because the hook content changed; status table semantics may need a note.

## Source

Source: /Users/paul/Private/Alfa/Projects/reestr.digital.gov.ru@not-a-git-repo
Reproducer evidence: COMMIT_EDITMSG below the scissor line contained the diff for `.claude/hooks/commit-msg-guard.sh`, whose body includes the literal forbidden-trailer regex. The Ralph commit-msg hook then matched that string and printed "BLOCKED: commit message contains forbidden trailer/heading."

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 templates/git-hooks/commit-msg strips the scissor section (`# ------------------------ >8 ------------------------` and everything below) from the message file before grepping — verified by inspecting the patched hook source
- [x] #2 A regression test under tests/ exercises the verbose-commit scenario: a fixture msg_file with a clean 'Initial commit' body, a scissor line, and a diff section that contains the literal forbidden trailer 'Co-Authored-By: x <y>' — running the patched hook on this fixture exits 0
- [x] #3 A negative test exercises a fixture whose author-body (above the scissor or with no scissor at all) contains the literal trailer 'Co-Authored-By: x <y>' — the patched hook still exits 1 and prints the BLOCKED diagnostic to stderr
- [x] #4 A negative test for the 'Generated with Claude Code' trailer in the author-body — patched hook exits 1
- [x] #5 A negative test for a '## Test plan' heading in the author-body — patched hook exits 1
- [x] #6 All existing tests/ still pass (run the project's documented test command, e.g. `bats tests/` or whatever `npm test` wires up)
- [x] #7 End-to-end repro check recorded in task notes: bootstrap a throwaway project with /ralph-init in this repo, set `git config commit.verbose true`, run `git commit -av` with the message body 'Initial commit', and confirm the commit succeeds (exit 0; git log shows the commit)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Use sed pipe to git stripspace per approach A discussed with user (source author's preferred approach B fails because stripspace --strip-comments only removes # lines, not diff body below scissor). New hook flow: sed strips from scissor line to EOF, then stripspace removes remaining # comments, then grep runs on cleaned text. Add 4 bats tests in tests/unit/commit-msg-hook.bats: positive (scissor-bug fixture passes), three negatives (Co-Authored-By, Generated-with, Test plan in author body all blocked). AC #7 e2e check: bootstrap throwaway project in /tmp via ralph-init, set commit.verbose true, verify git commit -av exits 0.

Implementation: patched skills/ralph-init/templates/git-hooks/commit-msg to strip the scissor section via sed '/^# -{1,} >8 -{1,}$/,$d' before grepping. Approach (b) git-stripspace --strip-comments was rejected because it also removes '## Test plan' (a # line) — broke AC #5 in initial run. Final hook uses sed alone. Added tests/unit/commit-msg-hook.bats with 9 cases: 1 positive (scissor regression), 3 negatives for each forbidden pattern in author body, 1 sanity-clean, 3 sanity-bypass (merge / fixup / squash). All 174 tests in npm test pass. AC #7 e2e: bootstrapped tmpdir/ralph-test-134, installed patched hook, set commit.verbose=true, exercised verbose-commit flow with a simulated editor that prepends 'Initial commit' — succeeded; throwaway repo recorded commit b9567f0 even though the staged file was .claude/hooks/commit-msg-guard.sh whose body contains the literal forbidden-trailer regex.
<!-- SECTION:NOTES:END -->
