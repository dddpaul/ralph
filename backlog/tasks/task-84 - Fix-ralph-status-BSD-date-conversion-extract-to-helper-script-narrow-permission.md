---
id: TASK-84
title: >-
  Fix ralph-status BSD date conversion + extract to helper script (narrow
  permission)
status: In Progress
assignee: []
created_date: '2026-05-01 18:02'
updated_date: '2026-05-01 18:13'
labels:
  - skills
  - ralph-status
  - permissions
  - bug
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-status SKILL.md Step 2.5 has two coupled problems:

1. BSD date conversion bug. The current fallback chain is:
     moscow_time=$(TZ=Europe/Moscow date -d "$utc_iso" "+%Y-%m-%d %H:%M:%S MSK" 2>/dev/null \
                   || TZ=Europe/Moscow date -j -f "%Y-%m-%dT%H:%M:%SZ" "$utc_iso" "+%Y-%m-%d %H:%M:%S MSK" 2>/dev/null)
   The BSD branch (`date -j -f`) does NOT honor the trailing Z. It parses the input as if it were in the LOCAL timezone, then formats it under TZ=Europe/Moscow. On a host whose local TZ is not UTC, the displayed time is offset by (local_offset - moscow_offset) hours. Concretely on a Moscow host that's 0 hours; on a UTC host that's -3 hours; on a US/Pacific host that's +10 hours. The output is silently wrong on most BSD/macOS installs.

   The correct BSD form is two steps that force UTC interpretation:
     epoch=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$utc_iso" "+%s")
     moscow_time=$(TZ=Europe/Moscow date -r "$epoch" "+%Y-%m-%d %H:%M:%S MSK")

2. Permission-prompt regression. The 2-step form starts with `epoch=$(date -j -u -f ...)` — a variable assignment with command substitution. Our existing rule `Bash(TZ=Europe/Moscow date:*)` only matches strings that START with that prefix; the compound command starts with `epoch=$(` and prompts for approval every ralph-status display.

Resolution: extract the conversion into a self-contained helper script next to the skill, expose ONE narrow permission rule for it. Same pattern as ralph-run's preflight.sh / wait-heartbeat.sh.

Implementation:

A. Add skills/ralph-status/scripts/utc-to-moscow.sh:
     #\!/usr/bin/env bash
     set -euo pipefail
     [ $# -eq 1 ] || { echo "usage: utc-to-moscow.sh <ISO 8601 UTC>" >&2; exit 2; }
     utc=$1
     # Try GNU date first (Linux / devcontainer), then BSD with -u for UTC parsing
     if out=$(TZ=Europe/Moscow date -d "$utc" "+%Y-%m-%d %H:%M:%S MSK" 2>/dev/null); then
       printf '%s\n' "$out"
       exit 0
     fi
     if epoch=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$utc" "+%s" 2>/dev/null); then
       TZ=Europe/Moscow date -r "$epoch" "+%Y-%m-%d %H:%M:%S MSK"
       exit 0
     fi
     echo "ERROR: could not parse '$utc' on either GNU or BSD date" >&2
     exit 1

B. Update skills/ralph-status/SKILL.md Step 2.5 to invoke the helper:
     moscow_time=$(bash <abs-path>/skills/ralph-status/scripts/utc-to-moscow.sh "$utc_iso")
   The path resolution rule mirrors ralph-run: prefer ./skills/..., then $HOME/.claude/skills/...

C. Update skills/ralph-status-watch/SKILL.md (Rule e timestamp conversion) the same way.

D. Add narrow permission rule to skills/ralph-init/templates/settings.local.json (immediately after the existing TZ=Europe/Moscow rule or in its place):
     "Bash(bash */utc-to-moscow.sh:*)"
   (literal-prefix won't match — same lesson as task-79; instead use $HOME-resolved rule via the same merge-step machinery in ralph-init Section 3.7 as preflight.sh/wait-heartbeat.sh)

E. Drop the now-unused `Bash(TZ=Europe/Moscow date:*)` rule from the template (the helper script now owns this) UNLESS another callsite still uses the inline form. Audit before removing.

F. Project-level apply-to-self:
   - Copy the helper to skills/ralph-status/scripts/utc-to-moscow.sh in this repo.
   - Mirror project skill changes to user-global ~/.claude/skills/ralph-status/ and ~/.claude/skills/ralph-status-watch/ so the loaded skills run the helper.
   - Update .claude/settings.local.json to add the $HOME-resolved narrow rule.

Out of scope: full audit of TZ-handling correctness in other skills; only ralph-status and ralph-status-watch are touched here.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-status/scripts/utc-to-moscow.sh exists, is executable, and accepts one ISO-8601 UTC argument
- [x] #2 Helper script tries GNU 'date -d' first and falls back to BSD 'date -j -u -f' with explicit UTC parsing; both branches output a single line in the form 'YYYY-MM-DD HH:MM:SS MSK'
- [x] #3 Helper script returns exit 1 with a stderr error message if neither branch can parse the input
- [x] #4 skills/ralph-status/SKILL.md Step 2.5 is updated to call the helper script (no inline TZ=Europe/Moscow date commands left in this step)
- [x] #5 skills/ralph-status-watch/SKILL.md (Rule e) is updated to call the helper script the same way
- [x] #6 skills/ralph-init/templates/settings.local.json contains the $HOME-resolved narrow rule for the helper, merged in by ralph-init Section 3.7 alongside preflight.sh and wait-heartbeat.sh (same pattern)
- [x] #7 ralph-init Section 3.7 merge step is extended to add the new utc-to-moscow.sh rule
- [x] #8 If 'Bash(TZ=Europe/Moscow date:*)' is no longer needed (i.e. no other callsite uses the inline form), it is removed from skills/ralph-init/templates/settings.local.json
- [x] #9 Project-level mirror: skills/ralph-status/scripts/utc-to-moscow.sh and SKILL.md updates also land in ~/.claude/skills/ralph-status/ (and ralph-status-watch) so the loaded skills run the helper without further sync
- [x] #10 Project .claude/settings.local.json is updated with the $HOME-resolved narrow rule for the helper
- [x] #11 Manual smoke test: on a non-UTC host, run ./scripts/utc-to-moscow.sh '2026-05-01T17:40:53Z' and confirm output is '2026-05-01 20:40:53 MSK' (UTC+3 fixed offset)
- [ ] #12 Manual smoke test: invoke /ralph-status against a finished run; the displayed completed_at line shows MSK without triggering a permission prompt
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Starting work: BSD date fix + helper script extraction

Plan: A) Create utc-to-moscow.sh helper, B) Update ralph-status SKILL.md Step 2.5, C) Update ralph-status-watch SKILL.md Rule e, D) Add narrow permission to settings.local.json template + merge step in ralph-init 3.7, E) Remove unused TZ=Europe/Moscow date rule, F) Mirror to user-global skills + project settings.local.json

Commit: `fc7e624` - task-84: Extract utc-to-moscow.sh helper for portable BSD/GNU date conversion
<!-- SECTION:NOTES:END -->
