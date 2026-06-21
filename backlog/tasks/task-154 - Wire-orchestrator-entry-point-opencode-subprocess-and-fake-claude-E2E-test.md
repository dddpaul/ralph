---
id: TASK-154
title: 'Wire orchestrator entry point, opencode subprocess, and fake-claude E2E test'
status: In Progress
assignee: []
created_date: '2026-06-21 13:09'
updated_date: '2026-06-21 20:15'
labels:
  - 'feature:ralph-python-refactor'
dependencies:
  - TASK-153
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-005 from design/ralph-python-refactor-prd.md.

Mirror the claude-code subprocess pattern for opencode, then assemble the full orchestrator entry point (argparse → preflight → main loop → final status write). End with an E2E test against a fake claude-code shim.

Spec sources:
- `skills/ralph-run/scripts/ralph.sh` lines 1–150 (CLI arg parsing, --help)
- `skills/ralph-run/scripts/ralph.sh` lines 560–650 (opencode / claude branch logic)
- `skills/ralph-run/scripts/ralph.sh` lines 850–895 (main loop + run summary)
- `design/ralph-python-refactor-prd.md` §6 "Fake claude-code Shim Modes" (fixture behavior contract)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `ralph/tools/opencode.py` implements `Tool.run()` for opencode using the same subprocess pattern as claude.py
- [x] #2 `ralph_orchestrator.py` entry point: argparse declares EXACT bash flag names (`--tool`, `--model`, `--effort`, `--timeout`, `--on-error`, `--retry-count`, `--log-file`, `--prompt-file`, `--tasks`, `--block-end-buffer-min`, `--devcontainer`) and positional `max_iterations` (nargs="?")
- [x] #3 Uses `parse_intermixed_args()`; no auto short-flag inference; ≥5 flag/positional ordering combinations covered by tests
- [x] #4 Path resolution honors `RALPH_PROJECT_ROOT` env var with `Path(__file__).parent` fallback
- [x] #5 Main loop: usage check → task pick → `MODE:` prefix + prompt build → tool invoke → signal parse → done-task diff → status update → sleep 2s
- [x] #6 `--prompt-file` REPLACES inner prompt body; `MODE:` prefix still prepended; missing file is hard fail exit 1 before loop starts
- [x] #7 Run summary printed on every exit path; exit_reason values are the closed set `{"all tasks done", "max iterations reached", "error", "interrupted"}`
- [x] #8 `tests/fixtures/fake_claude.py` shim implements 4 modes via `FAKE_CLAUDE_MODE` env var: success (default — edits a backlog task), task_done_no_summary, fail, hang
- [x] #9 E2E test `tests/test_e2e_fake_claude.py`: orchestrator runs against `fake_claude.py` in success mode; asserts `state=completed`, `exit_code=0`, `errors=[]`, `tasks_done` includes the fake-marked task
- [x] #10 `uv run pyright skills/ralph-run/scripts` passes
- [x] #11 `uv run ruff check skills/ralph-run/scripts` passes
- [x] #12 `uv run pytest skills/ralph-run/tests/` passes
<!-- AC:END -->

























## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) opencode.py mirrors claude.py but invokes 'opencode run <PROMPT>' (prompt is positional arg, not stdin). Reuse _execute() helper. (2) ralph_orchestrator.py grows into full entry: argparse w/ allow_abbrev=False + parse_intermixed_args, all 11 flags + max_iterations positional, RALPH_PROJECT_ROOT path resolver, validators (TOOL, EFFORT, ON_ERROR, TIMEOUT, RETRY_COUNT, BLOCK_END_BUFFER, TASKS), prompt builder (whitelist > prompt-file > default), main loop with usage check, task pick, MODE: prefix, tool invoke, signal parse, done diff, status update, 2s sleep, summary on every exit. (3) fake_claude.py with 4 modes via FAKE_CLAUDE_MODE. (4) test_e2e_fake_claude.py: bootstrap tmpdir backlog (mock backlog CLI on PATH), run orchestrator, assert status JSON has state=completed/exit_code=0/errors=[]/tasks_done populated. (5) Unit tests: opencode argv, parse_intermixed flag ordering combos, prompt-file behavior, RALPH_PROJECT_ROOT honor.
<!-- SECTION:NOTES:END -->
