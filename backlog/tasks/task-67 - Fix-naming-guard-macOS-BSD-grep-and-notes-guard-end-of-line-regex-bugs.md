---
id: TASK-67
title: Fix naming-guard macOS BSD grep and notes-guard end-of-line regex bugs
status: Done
assignee: []
created_date: '2026-04-30 12:29'
updated_date: '2026-04-30 12:35'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two hook bugs found during code review of TASK-66.

## Bug 1: naming-guard.sh fails silently on macOS

**File:** `.claude/hooks/naming-guard.sh` lines 15 and 23.

**Problem:** uses `grep -qP '[^\x00-\x7F]'` (Perl-compatible regex). macOS BSD grep does NOT support `-P` — the flag returns "invalid option" / exit code 2. Inside `if ... | grep -qP ...; then`, this evaluates as no match, so non-ASCII titles slip past the guard silently. The hook exits 0 and the forbidden `backlog task create \"Привет\"` succeeds.

**Fix options (pick one):**
- Bash native: `[[ \$title == *[^[:ascii:]]* ]]` — no external grep dependency
- Portable: `LC_ALL=C grep -q '[^[:print:][:space:]]'` (matches non-ASCII via byte class)

Apply the same fix to lines 15 (title check) and 23 (branch_name check). Update the matching template at `skills/ralph-init/templates/...` (currently the hooks are inlined into settings.json — verify whether the inline copy in `.claude/settings.json` and `skills/ralph-init/templates/settings.json` need the same fix).

## Bug 2: notes-guard.sh misses --notes at end of line

**File:** `.claude/hooks/notes-guard.sh` line 12.

**Problem:** regex ` --notes[= ]` requires a space or `=` immediately after `--notes`. The case `backlog task edit 5 --notes` (with `--notes` at end of command, no value) is NOT caught. Claude could trigger the destructive `--notes` path with this form.

**Fix:** change pattern to ` --notes([= ]|\$)` — anchors to end of line as alternative. Or use word boundary: ` --notes\b` and explicitly exclude the `-append-notes` case (which the existing `\! grep --append-notes` line already does).

Apply the fix to `.claude/hooks/notes-guard.sh` AND to the inline command in `.claude/settings.json` AND to the matching template in `skills/ralph-init/templates/settings.json`.

## Smoke tests required after fix

- `backlog task create \"Привет\"` → BLOCKED with naming-guard error (currently passes through)
- `backlog task create \"Hello\" -d \"Привет описание\"` → succeeds (description allowed any language)
- `git checkout -b task-99-привет` → BLOCKED
- `git checkout -b task-99-hello` → succeeds
- `backlog task edit 5 --notes` → BLOCKED (currently passes through)
- `backlog task edit 5 --notes \"foo\"` → BLOCKED
- `backlog task edit 5 --notes=foo` → BLOCKED
- `backlog task edit 5 --append-notes \"foo\"` → succeeds
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 naming-guard.sh replaces grep -qP with portable check (bash [[ ]] or LC_ALL=C grep)
- [x] #2 notes-guard.sh regex catches --notes at end of command (no value)
- [x] #3 Inline hook commands in .claude/settings.json updated with same fixes
- [x] #4 Inline hook commands in skills/ralph-init/templates/settings.json updated with same fixes
- [x] #5 Smoke test: backlog task create with Cyrillic title is BLOCKED on macOS
- [x] #6 Smoke test: backlog task edit with bare --notes at end is BLOCKED
- [x] #7 All other smoke tests from TASK-66 still pass (regression check)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Starting work on TASK-67

Plan: (1) Fix naming-guard.sh lines 15,23: replace grep -qP with bash [[ *[^[:ascii:]]* ]] check. (2) Fix notes-guard.sh line 12: change regex to catch --notes at EOL. (3) Apply same fixes to inline hooks in .claude/settings.json and templates/settings.json. (4) Smoke test all cases.

Commit: `247258d` - task-67: Fix naming-guard BSD grep and notes-guard EOL regex bugs

All fixes applied and verified. Code review approved. Portable LC_ALL=C grep replaces grep -qP; notes-guard regex catches bare --notes at EOL.
<!-- SECTION:NOTES:END -->
