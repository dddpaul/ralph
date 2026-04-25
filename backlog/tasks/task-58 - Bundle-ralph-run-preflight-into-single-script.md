---
id: TASK-58
title: Bundle ralph-run preflight into single script
status: Done
assignee:
  - '@claude'
created_date: '2026-04-25 09:09'
updated_date: '2026-04-25 10:02'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace the inline precondition checks (Steps 3.1-3.4 in skills/ralph-run/SKILL.md) with a single preflight.sh script that runs all checks and prints OK or ERROR: <reason>.

## Context

Currently /ralph-run makes 6-8 separate Bash tool calls before launching:
1. backlog task list -s 'To Do'
2. grep state/pid from .ralph-status.json
3. stat heartbeat
4. command -v devcontainer (if devcontainer=true)
5. test -x ralph.sh
6. bash -n ralph.sh syntax check
7. nohup launch
8. post-launch stat

Each is a separate tool block — verbose, noisy, and slow. Goal: collapse all preflight checks (1-6) into a single bundled script, so the user sees one preflight call instead of five-plus.

## Files involved

- skills/ralph-run/SKILL.md — replace Step 3 (Validate Preconditions) with a single instruction to run preflight.sh
- skills/ralph-run/scripts/preflight.sh — NEW script
- skills/ralph-run/scripts/preflight_test.sh — NEW automated test
- skills/ralph-init/templates/settings.local.json — add matching Bash allow entry (mandatory)
- .claude/settings.local.json — same allow entry for local project settings (mandatory)

## Script contract

Usage: preflight.sh <ralph_path> <devcontainer:true|false>

Working directory: preflight.sh MUST operate against the invoker's CWD (the project root containing backlog/). It must NOT cd elsewhere and must NOT assume its own location matches the project root — the script may live under ~/.claude/skills/ralph-run/scripts/ when installed, while the project is elsewhere. All path lookups for backlog/, ralph.sh, and .ralph-status.json must be relative to PWD as observed at script start.

On success, print exactly one line:
  OK RALPH_PATH=<path>

On failure, print exactly one line:
  ERROR: <user-facing reason>

Internal checks (in order, fail-fast — 5 checks total):
1. To Do tasks exist (backlog task list -s 'To Do' --plain — must list at least one task)
2. Ralph not already running: read backlog/.ralph-status.json; if state==running and heartbeat mtime within 15s of now → fail
3. If devcontainer=true: command -v devcontainer must succeed
4. ralph.sh is executable (test -x <ralph_path>)
5. ralph.sh has valid syntax (bash -n) — write stderr to "$TMPDIR/ralph-syntax-err.$$" and clean up after

(SKILL.md groups checks 4 and 5 under "3.4 ralph.sh integrity"; splitting them here keeps per-check logging clean for the verbose mode in TASK-61.)

## Permissions update (mandatory)

Both settings.local.json files (skills/ralph-init template AND .claude/ local) MUST add an allow pattern matching how SKILL.md invokes preflight.sh. If SKILL.md calls bash skills/ralph-run/scripts/preflight.sh ..., the allow entry must be Bash(bash skills/ralph-run/scripts/preflight.sh:*) or equivalent. After install there should be no new approval prompts on the preflight step.

## SKILL.md changes

Replace Steps 3.1-3.4 with one block: "Run scripts/preflight.sh <ralph_path> <devcontainer-flag>. If output starts with OK, parse RALPH_PATH and proceed to Step 4. If it starts with ERROR:, report the message verbatim and stop." Step 2, Step 4, and Step 5 are unchanged in this task.

## Testing

Add skills/ralph-run/scripts/preflight_test.sh — automated test suite covering: empty backlog → ERROR; fresh ralph already running (mock heartbeat) → ERROR; devcontainer=true with missing CLI → ERROR; ralph.sh missing chmod +x → ERROR; ralph.sh syntax broken → ERROR; valid setup → OK RALPH_PATH=.... Tests use $TMPDIR for fixtures, exit non-zero on any failure, and are callable from a fresh repo state. Ralph must run this script as the verification step before marking the task Done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-run/scripts/preflight.sh exists and is chmod +x
- [x] #2 preflight.sh performs all 5 checks in order (To Do tasks, ralph not running, devcontainer CLI if requested, ralph.sh executable, ralph.sh syntax valid)
- [x] #3 preflight.sh prints exactly one line on success: OK RALPH_PATH=<path>
- [x] #4 preflight.sh prints exactly one line on failure: ERROR: <reason>
- [x] #5 preflight.sh uses $TMPDIR for temp files and cleans them up; zero references to /tmp
- [x] #6 preflight.sh operates against PWD (invoker's CWD) for backlog/ and .ralph-status.json lookups; no cd, no $0-relative project paths
- [x] #7 skills/ralph-run/SKILL.md Step 3 is replaced with one instruction to run preflight.sh and parse OK/ERROR; Steps 2, 4, 5 are unchanged
- [x] #8 Both skills/ralph-init/templates/settings.local.json AND .claude/settings.local.json have the matching Bash(...preflight.sh:*) allow entry
- [x] #9 skills/ralph-run/scripts/preflight_test.sh exists, is chmod +x, exercises each failure path plus the OK path, and exits non-zero on any failure
- [x] #10 preflight_test.sh passes from a clean state — Ralph must run it as the verification step before marking Done
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Create scripts/preflight.sh with 5 checks (To Do tasks, ralph not running, devcontainer CLI, ralph.sh executable, ralph.sh syntax). 2) Create scripts/preflight_test.sh with test cases for each failure path + success path. 3) Update SKILL.md Step 3 to call preflight.sh. 4) Add Bash allow entries in both settings.local.json files. Script operates against PWD, uses TMPDIR for temp files, prints exactly one line (OK or ERROR).

Commit: `7935424` - task-58: Preflight script for ralph-run precondition checks

Implemented preflight.sh bundling 5 precondition checks into a single script. Created preflight_test.sh with 6 test cases. Updated SKILL.md Step 3 to single preflight call. Added Bash allow entries in both settings.local.json files. Files: scripts/preflight.sh, scripts/preflight_test.sh, SKILL.md, templates/settings.local.json, .claude/settings.local.json.
<!-- SECTION:NOTES:END -->
