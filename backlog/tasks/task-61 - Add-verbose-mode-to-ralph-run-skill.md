---
id: TASK-61
title: Add verbose mode to ralph-run skill
status: Done
assignee:
  - '@claude'
created_date: '2026-04-25 09:10'
updated_date: '2026-04-25 10:11'
labels: []
dependencies:
  - TASK-58
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add an opt-in verbose=true argument to /ralph-run that makes preflight.sh print check-by-check output instead of just OK/ERROR.

## Context

After TASK-58 collapses preflight into a single script with one-line OK/ERROR output, users debugging launch failures lose visibility into which check passed or failed. Add verbose=true as an opt-in escape hatch for diagnostics.

## Dependency

Depends on TASK-58 — verbose mode is a flag on preflight.sh, which doesn't exist until TASK-58 lands. Pick TASK-58 first.

## Files involved

- skills/ralph-run/scripts/preflight.sh — accept --verbose flag, print intermediate check results when set
- skills/ralph-run/SKILL.md — Step 1 (parse args) documents verbose=true; Step 3 forwards --verbose to preflight.sh when set

## Behavior

Default (verbose unset or false):
- preflight.sh prints exactly one line: OK ... or ERROR: ...

verbose=true:
- preflight.sh prints one line per check: e.g., 'check todo_tasks: ok (3 tasks)', 'check ralph_running: ok (no fresh heartbeat)', 'check devcontainer_cli: ok', 'check ralph_executable: ok', 'check ralph_syntax: ok', then the final OK/ERROR line

## Out of scope

verbose flag does not affect Step 5 (success/failure report) — that's TASK-59's domain. verbose only affects preflight output.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-run/scripts/preflight.sh accepts a --verbose flag
- [x] #2 Without --verbose, preflight.sh prints exactly one line (OK ... or ERROR: ...)
- [x] #3 With --verbose, preflight.sh prints one 'check <name>: <result>' line per check, then the final OK/ERROR line
- [x] #4 skills/ralph-run/SKILL.md Step 1 (Parse Arguments) documents verbose as a parameter with default false
- [x] #5 skills/ralph-run/SKILL.md Step 3 forwards --verbose to preflight.sh when verbose=true
- [x] #6 Default invocation (/ralph-run with no args) still produces single-line preflight output
- [x] #7 preflight_test.sh includes at least one test case that runs preflight.sh with --verbose and asserts per-check output lines appear before the final OK/ERROR line
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Add --verbose flag parsing to preflight.sh, (2) wrap each check with verbose output via helper function, (3) update SKILL.md Step 1 and Step 3 for verbose parameter, (4) add verbose test case to preflight_test.sh

Commit: `c44d851` - task-61: Add --verbose flag to preflight.sh

Implemented --verbose flag on preflight.sh with per-check output lines. Updated SKILL.md parameter table and Step 3 docs. Added 2 test cases (verbose OK + verbose ERROR) to preflight_test.sh. All 8 tests pass.
<!-- SECTION:NOTES:END -->
