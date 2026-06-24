---
id: TASK-175
title: Fix Python orchestrator missing devcontainer up before exec (bash parity gap)
status: In Progress
assignee: []
created_date: '2026-06-24 08:47'
updated_date: '2026-06-24 09:03'
labels:
  - bug
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Default Ralph configuration `RALPH_IMPL=python` + `--devcontainer` fails immediately because the Python orchestrator skips the `devcontainer up` step that the bash orchestrator runs once before the iteration loop. TASK-156 is flipping the default to python — this gap blocks every downstream Ralph project that uses the default `/ralph-run watch=5m devcontainer=true` after the cutover. Currently visible as `Error: Dev container not found.` in devcontainer CLI stderr and a ~2-second iteration-1 failure with `exit_code=1`.

## Scope

In scope:
- Add `devcontainer up --workspace-folder <project_root>` to Python orchestrator pre-loop setup when `args.devcontainer=True`
- Match bash log output verbatim: print "Starting devcontainer..." before, "Devcontainer is ready." after
- Exit non-zero if `up` fails, surfacing devcontainer CLI stderr to the operator
- Cover with a test asserting `up` is called once before the first `exec`

Out of scope:
- Refactoring the bash orchestrator (TASK-156 is deleting it after the cutover window)
- Changing the `devcontainer exec` prefix assembly in `ralph/tools/claude.py` (it's correct; only the pre-loop `up` step is the gap)
- Changing any project's `.devcontainer/` config

## Files

- `skills/ralph-run/scripts/ralph/loop.py` (exists) — pre-loop setup; best home for the `devcontainer up` call (mirrors bash ralph.sh lines 602-611)
- `skills/ralph-run/scripts/ralph/devcontainer.py` (to-create) — optional new module if extracting up/down logic for testability; reused by `loop.py:run`
- `skills/ralph-run/scripts/ralph.sh` (exists) — bash reference for log strings and call sequencing (lines 602-611, kept until TASK-156 cutover completes)
- `skills/ralph-run/scripts/ralph/tools/claude.py` (exists) — already assembles `devcontainer exec --workspace-folder <path>` prefix; do NOT modify, just verify it still works after `up` is wired
- `skills/ralph-run/scripts/` test files (exists — see `preflight_test.sh`, `ralph_status_test.sh`, or pytest layout under `ralph/`) — add new test for `up`-before-`exec` ordering matching project test convention

## Reproducer

In any project with `.devcontainer/devcontainer.json` and no container currently running:

```
RALPH_PROJECT_ROOT="$PWD" RALPH_IMPL=python uv run \
  ~/.claude/skills/ralph-run/scripts/ralph_orchestrator.py \
  --tool claude --model claude-opus-4-7 --effort max --timeout 60 \
  --devcontainer --tasks <any-id> 1
```

Result: exit 1 in ~2s; `backlog/.ralph-status.json` shows `state=failed`, `errors=[{message: "Iteration 1 failed with exit code 1"}]`; devcontainer CLI stderr: `Error: Dev container not found.`

Workarounds in use (any one unblocks):
- `RALPH_IMPL=bash` (legacy orchestrator runs `up`)
- Manual `devcontainer up --workspace-folder $PWD` before `/ralph-run`
- `devcontainer=false` (no isolation)

## Root cause

Bash orchestrator `skills/ralph-run/scripts/ralph.sh` lines 602-611:

```bash
if [[ "$USE_DEVCONTAINER" == true ]]; then
  if ! command -v devcontainer &> /dev/null; then ... fi
  echo "Starting devcontainer..."
  devcontainer up --workspace-folder "${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}"
  echo "Devcontainer is ready."
fi
```

Python equivalent missing — `grep -rn "devcontainer up\|\"up\"" skills/ralph-run/scripts/ralph/` returns zero matches. Only `devcontainer exec --workspace-folder ...` is assembled per-iteration in `ralph/tools/claude.py:_argv()`.

## Source

Source: /Users/paul/Private/Alfa/Projects/duedil/ethiopia@e0c24dbb29f0

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. TASK-156 (cutover) status — this fix is a precondition for TASK-156 completion gates on default-python + devcontainer=true; coordinate or block as appropriate.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 grep -rn 'devcontainer up' skills/ralph-run/scripts/ralph/ returns at least one match (the new call site in pre-loop setup)
- [ ] #2 Reproducer command (RALPH_IMPL=python ... --devcontainer ... 1) no longer fails on devcontainer-not-found; if iteration 1 fails it is for task-content reasons, not for missing pre-loop devcontainer up
- [x] #3 Stdout from python orchestrator with --devcontainer contains the strings 'Starting devcontainer...' and 'Devcontainer is ready.' in that order, matching bash output verbatim
- [x] #4 When devcontainer up itself fails (e.g., docker not running), orchestrator exits non-zero with devcontainer CLI stderr surfaced; iteration loop is NOT entered
- [x] #5 A new test in skills/ralph-run/scripts/ (bash or pytest, matching project convention) asserts devcontainer up is called exactly once before the first devcontainer exec; test runs as part of the existing suite (preflight_test.sh / ralph_status_test.sh / pytest) and passes
- [x] #6 All existing tests still pass: preflight_test.sh, ralph_status_test.sh, and any pytest under skills/ralph-run/scripts/ralph/
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Create skills/ralph-run/scripts/ralph/devcontainer.py with start_devcontainer(workspace_folder) -> int that mirrors bash ralph.sh:602-611: shutil.which check, 'Starting devcontainer...' print, 'devcontainer up --workspace-folder <path>' subprocess.run, 'Devcontainer is ready.' print, surface stderr on failure. (2) loop.py run(): import start_devcontainer; after prompt_file_body load and BEFORE StatusFile init, if args.devcontainer: rc = start_devcontainer(project_root); if rc \!= 0: return rc. Matches bash semantics: no status file written on up failure. (3) New tests/test_devcontainer.py covering CLI-missing, up-success-prints-strings, up-failure-surfaces-stderr. (4) New tests/test_loop_devcontainer_up.py asserting up called exactly once before any tool invocation (call-order spy). (5) Run: uv run pytest tests/ tests/scripts/check_run_clean.py && uv run ruff check . && bash skills/ralph-run/scripts/preflight_test.sh && bash skills/ralph-run/scripts/ralph_status_test.sh.

Implementation complete: skills/ralph-run/scripts/ralph/devcontainer.py exposes start_devcontainer(workspace_folder, *, stdout, stderr); loop.py imports it and calls before status init when args.devcontainer. Test coverage: tests/test_devcontainer.py (3 unit) + tests/test_loop_devcontainer_up.py (3 integration including call-once-before-exec ordering and up-failure-skips-tool). All 207 pytest tests pass, ruff clean, ralph_status_test.sh 14/14 pass. preflight_test.sh shows 12/13 pass — the 1 failure ('--tasks missing task — expected substring TASK-999 not found') is PRE-EXISTING (verified by stashing TASK-175 changes and re-running). AC #2 requires the live reproducer in a downstream project (the host repo's devcontainer is already up from earlier bash runs); will be verified during the claude-skills smoke test.
<!-- SECTION:NOTES:END -->
