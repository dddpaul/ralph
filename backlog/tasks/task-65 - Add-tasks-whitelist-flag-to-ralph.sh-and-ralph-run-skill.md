---
id: TASK-65
title: Add --tasks whitelist flag to ralph.sh and ralph-run skill
status: Done
assignee:
  - '@claude'
created_date: '2026-04-26 19:50'
updated_date: '2026-04-26 20:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently ralph.sh always picks the next To Do task by lowest-ID (per CLAUDE.md). Add an optional `--tasks` flag that constrains Ralph to a specific whitelist of task IDs. When omitted, current behavior is preserved.

## Behavior

**No `--tasks`:** unchanged — loop picks next To Do task each iteration, exits when To Do is empty or max_iterations hit.

**With `--tasks 62,64,65`:**
- Loop runs only these tasks, in the order listed
- Each iteration: pick first whitelisted ID still in To Do status, inject into prompt
- Exit cleanly with `all specified tasks done` when all are Done
- Mutually exclusive with `--prompt-file` (refuse at preflight)

## ralph.sh changes

**Flag parser:** `--tasks <ids>` accepts comma-separated numeric IDs only (regex `^[0-9]+(,[0-9]+)*$`). Reject `TASK-` prefix or any non-digit. Store as bash array `TASK_WHITELIST`.

**Preflight validation** (after arg parsing, before main loop): for each ID, run `backlog task <id> --plain`. If task missing → `ERROR: TASK-<id> not found in backlog` exit 1. If status not exactly `To Do` → `ERROR: TASK-<id> is not To Do (status: <status>)` exit 1. Log success: `Restricted to: TASK-62, TASK-64, TASK-65 (3 tasks)`.

**Mutual exclusion:** if both `--tasks` and `--prompt-file` are set, `ERROR: --tasks and --prompt-file are mutually exclusive` exit 1.

**Main loop changes** (only when whitelist active):
- Replace `backlog task list -s 'To Do'` polling with: iterate whitelist, find first ID whose current status is still `To Do` (re-query each iteration). If none remain → `EXIT_REASON='all specified tasks done'` exit 0.
- `CURRENT_TASK=TASK-<id>` (status JSON unchanged)
- Targeted prompt body: `Execute TASK-<id> using the full Task Lifecycle from CLAUDE.md. Do NOT pick any other task. If TASK-<id> is already Done, reply with <promise>COMPLETE</promise>. Your response MUST end with the ## Task Summary block. This is not optional.`

**Status file `tasks_remaining`:** when whitelist active, count remaining whitelist IDs whose status is To Do. Otherwise, current logic.

**Help text:** add `--tasks <ids>` line documenting numeric-only IDs and mutual exclusion with `--prompt-file`.

## preflight.sh changes

**New flag:** `--tasks <ids>` (same parser rules as ralph.sh).

**When `--tasks` is passed**, replace Check 1 ("To Do tasks exist") with strict per-ID validation:
1. `backlog task <id> --plain` for each ID
2. Missing task → `ERROR: TASK-<id> not found in backlog`
3. Status \!= `To Do` → `ERROR: TASK-<id> is not To Do (status: <status>)`
4. Verbose: `check tasks_whitelist: ok (N tasks)`

When `--tasks` not passed, Check 1 stays as today.

## ralph-run skill changes

Add `tasks` parameter to argument table (default: empty/none, flag: `--tasks`).

In SKILL.md Step 1: validate `tasks` value matches `^[0-9]+(,[0-9]+)*$`, refuse otherwise.

In SKILL.md Step 3: when `tasks` is set, append `--tasks <ids>` to the preflight invocation.

In SKILL.md Step 4: when `tasks` is set, append `--tasks <ids>` to the ralph.sh launch command.

Examples:
- `/ralph-run` — current behavior
- `/ralph-run tasks=62` — only TASK-62
- `/ralph-run tasks=62,64,65 max_iterations=3`

## Tests (bats suite)

- `--tasks 62` parses and stores correctly
- `--tasks abc` rejected with clear error
- `--tasks 62,abc` rejected
- `--tasks 999` (non-existent) rejected at preflight
- `--tasks 1` (Done task) rejected at preflight
- `--tasks` + `--prompt-file` rejected as mutually exclusive
- Whitelist exhaustion exits 0 with `all specified tasks done` reason
- No `--tasks` regression: existing behavior unchanged
- preflight_test.sh: --tasks valid, --tasks missing, --tasks Done, --tasks non-numeric

## README

Add `--tasks` row to flags table with one-line description and example.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph.sh accepts --tasks flag with comma-separated numeric IDs (regex ^[0-9]+(,[0-9]+)*$); rejects TASK- prefix and non-numeric values
- [x] #2 ralph.sh --tasks fails fast at preflight if any listed ID is missing from backlog or not in To Do status
- [x] #3 ralph.sh --tasks and --prompt-file are mutually exclusive (preflight error if both set)
- [x] #4 Main loop with --tasks active picks first whitelisted ID still in To Do, exits cleanly with 'all specified tasks done' when whitelist is exhausted
- [x] #5 Targeted prompt 'Execute TASK-<id> using the full Task Lifecycle...' is sent each iteration when whitelist active
- [x] #6 Status file tasks_remaining reflects remaining whitelist IDs (not total To Do) when whitelist active
- [x] #7 preflight.sh accepts --tasks flag and performs strict per-ID validation, replacing the generic Check 1 when active
- [x] #8 ralph-run skill accepts tasks=<ids> argument, validates format, forwards to both preflight.sh and ralph.sh
- [x] #9 Without --tasks, ralph.sh, preflight.sh, and ralph-run skill behave identically to current implementation (regression test)
- [x] #10 ralph.sh --help and README document the new --tasks flag
- [x] #11 CLAUDE.md (project root) Ralph Loop section branches on whether the prompt names a task: (1) prompt names task → execute it directly, (2) otherwise → pick lowest-ID To Do
- [x] #12 skills/ralph-init/templates/CLAUDE.md gets the same Ralph Loop update so new projects bootstrap with task-aware picking logic
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## CLAUDE.md update (added during brainstorm review)

The Ralph Loop section in CLAUDE.md tells the agent to pick the lowest-ID To Do task each iteration. With --tasks active, ralph.sh injects a targeted prompt that names a specific task ID. The CLAUDE.md picking instructions conflict with the targeted prompt — strong prompt language probably wins, but it's fragile.

**Fix:** update the Ralph Loop section to branch on whether the prompt names a specific task:

```
## Ralph Loop (Autonomous Mode)

Activated when the prompt starts with `MODE: autonomous`. Task selection:

1. **If the prompt explicitly names a task** (e.g. "Execute TASK-62"): work on that
   task only. Do not consult the To Do list for picking.
2. **Otherwise:** Run `backlog task list -s "To Do" --plain` and pick the task
   with the lowest ID whose dependencies are all "Done".
3. Read details, execute the Task Lifecycle, then STOP.
```

Apply the same change to both:
- CLAUDE.md (project root, used by ralph.sh each iteration)
- skills/ralph-init/templates/CLAUDE.md (so new projects bootstrap with the right version)

Plan:
1. ralph.sh: Add --tasks flag parsing, validation, mutual exclusion with --prompt-file, whitelist-aware main loop, count_remaining_tasks override
2. preflight.sh: Add --tasks flag parsing and per-ID validation replacing Check 1
3. ralph-run SKILL.md: Add tasks parameter to argument table, forward to preflight and ralph.sh
4. CLAUDE.md (root): Update Ralph Loop section with task-aware picking
5. skills/ralph-init/templates/CLAUDE.md: Same Ralph Loop update
6. README.md: Add --tasks row to CLI options table
7. Tests: argument-validation.bats for --tasks, preflight_test.sh for --tasks validation
8. Bundled ralph.sh: Update skills/ralph-run/scripts/ralph.sh to match root ralph.sh

Commit: `b454139` - task-65: --tasks whitelist flag for ralph.sh and ralph-run skill

Implemented --tasks whitelist flag across ralph.sh, preflight.sh, ralph-run skill, CLAUDE.md (root + template), and README. 14 new tests (8 unit, 1 integration, 5 preflight). All 140 tests pass. Code review approved.
<!-- SECTION:NOTES:END -->
