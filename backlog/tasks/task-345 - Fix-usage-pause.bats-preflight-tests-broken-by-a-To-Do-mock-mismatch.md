---
id: TASK-345
title: Fix usage-pause.bats preflight tests broken by a To-Do mock mismatch
status: Done
assignee: []
created_date: '2026-11-09T06:36:00Z'
updated_date: '2026-11-09T07:16:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: the 2026-11-08 feature review follow-up from TASK-342/343. tests/integration/usage-pause.bats tests 1-3 (the preflight ones) fail on master, and already failed at 3e125d7 (before TASK-342/343), both inside and outside the devcontainer sandbox. Test 4 passes.

Cause: tests/helpers/common.bash's mock_backlog() installs a fake 'backlog' executable that just echoes a fixed string regardless of arguments:

```bash
mock_backlog() {
  local response="$1"
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/backlog" <<EOF
#!/bin/bash
echo "$response"
EOF
  chmod +x "$TEST_DIR/bin/backlog"
  export PATH="$TEST_DIR/bin:$PATH"
}
```

Tests 1-3 in usage-pause.bats call it as 'mock_backlog "TASK-1 - test"'. preflight.py's _check_todo_tasks (plugins/ralph/skills/ralph-run/scripts/ralph/preflight.py:215-222) then runs 'backlog task list -s "To Do" --plain' and checks:

```python
def _check_todo_tasks(verbose: bool) -> int:
    out = _backlog_stdout(["task", "list", "-s", "To Do", "--plain"])
    if "No tasks found" in out or "TASK-" not in out:
        print("ERROR: No To Do tasks in backlog")
        return 1
```

which prints 'ERROR: No To Do tasks in backlog' (the exact line the three failing tests hit) even though the mocked output contains the literal substring 'TASK-'. Reproduce inside the devcontainer (or on a host with bats installed) with: 'bats tests/integration/usage-pause.bats'. Investigate why the substring check does not pass against the mock's actual output in this call path (one candidate: _backlog_stdout or an earlier check in the same preflight invocation consumes/alters PATH or stdout before _check_todo_tasks runs; verify directly rather than assuming) and fix whichever side (the mock in tests/helpers/common.bash, or _check_todo_tasks's parsing) is wrong, so it matches real 'backlog task list -s "To Do" --plain' output shape without weakening the real check.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/integration/usage-pause.bats tests 1 through 4 all pass, both inside and outside the devcontainer sandbox
- [x] #2 Root cause (mock defect vs. parser defect) is recorded in the task's implementation notes
- [x] #3 If the fix touches plugins/ralph/skills/ralph-run/scripts/ralph/preflight.py (a shipped file), the plugin version is bumped per the Merge-step Task Lifecycle; if the fix is confined to tests/, no version bump is needed
- [x] #4 _check_todo_tasks's real-world behavior against actual 'backlog task list -s "To Do" --plain' output is unchanged (verified by the existing non-mocked preflight tests still passing)
- [x] #5 bash -n and the bash 3.2 static guard (R-INFRA-3) pass on any changed shell script
- [x] #6 ruff, pytest and the full bats suite all pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: reproduce usage-pause.bats 1-3; trace why preflight's backlog call misses the mock; fix the PATH resolution in the shipped preflight shim/module and add pytest coverage.

Commit: `0577c2f` - task-345: resolve preflight tools on the caller's PATH, not uv's interpreter bin dir

Root cause: neither a mock defect nor a parser defect. preflight.sh execs 'uv run --no-project python -m ralph.preflight', and uv run puts the interpreter environment's bin directory first on PATH, ahead of the test's $TEST_DIR/bin. On macOS with Homebrew Python that directory is /opt/homebrew/bin, which also holds the real backlog CLI; it shadows mock_backlog, runs against the empty $TEST_DIR/backlog and prints 'No tasks found', so _check_todo_tasks correctly reports 'ERROR: No To Do tasks in backlog'. Test 4 passes because ralph.sh runs the orchestrator as a PEP 723 script in an ephemeral env whose bin dir has no backlog. On this Linux devcontainer the uv-managed interpreter bin has no backlog, so 1-3 pass; reproduced 1-3 failing / 4 passing here with UV_PYTHON pointing at a venv whose bin holds a 'No tasks found' backlog. Fix (shipped): preflight.sh passes the caller's PATH as RALPH_CALLER_PATH and preflight.main() restores it first (_restore_caller_path), so backlog/devcontainer/ccusage resolve the way the caller sees them; _check_todo_tasks and the mocks are unchanged. Tests: test_caller_path_wins_over_uv_interpreter_bin (in-process) and test_shim_resolves_backlog_on_caller_path (end-to-end shim against a uv venv with a shadowing backlog; fails without the fix). Checks: ruff clean; pytest 1607 passed, 4 skipped; bats -r tests/ 286/286; usage-pause.bats 4/4 both normally and with UV_PYTHON set to the shadowing venv; bash -n preflight.sh ok, test_bash32_syntax passes. Not run on macOS itself. Version bump (AC #3) happens at merge via bump-version.sh --auto.

Review: APPROVED 0577c2f46db5da8fd245c91ade0ae215b918b2d0

Commit: `2be2801` - task-345: bump plugin version to 0.25.14 (patch)

Done: plugin bumped to 0.25.14 (2be2801) by bump-version.sh --auto since preflight.sh/preflight.py are shipped. Final ruff clean, full pytest 1607 passed / 4 skipped and bats 286/286 on the reviewed tree (the bump only touches the two manifests).
<!-- SECTION:NOTES:END -->
