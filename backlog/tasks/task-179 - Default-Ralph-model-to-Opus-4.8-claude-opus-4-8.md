---
id: TASK-179
title: Default Ralph model to Opus 4.8 (claude-opus-4-8)
status: Done
assignee: []
created_date: '2026-06-28 13:27'
updated_date: '2026-06-28 13:56'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bump the default --model from claude-opus-4-7 to claude-opus-4-8 (Opus 4.8, the latest Opus) across the Ralph orchestrator and the ralph-run skill so new runs use 4.8 without an explicit override.

Canonical default lives in the Python orchestrator: skills/ralph-run/scripts/ralph/args.py:81 — parser.add_argument('--model', default='claude-opus-4-7'). The ralph-run SKILL.md defaults table (line ~21) and the divergence note (line ~49) pin the same string and must match.

Load-bearing test: skills/ralph-run/tests/test_orchestrator_args.py:78 asserts parsed.model == 'claude-opus-4-7' for the no-flag default — this MUST flip to claude-opus-4-8 or it fails.

Consistency sweep (no behavior impact, but avoids a mixed 4-7/4-8 codebase): the explicit fixture inputs model='claude-opus-4-7' in test_loop_exit_code.py, test_loop_max_iter_summary.py, test_loop_whitelist_summary.py, test_loop_paused_summary.py, test_loop_whitelist_tasks_remaining.py, test_loop_devcontainer_up.py, and test_tool_claude.py (input + assertion) should also move to claude-opus-4-8 so all live references agree. Leave docstring examples (e.g. tools/claude.py:60 'e.g. claude-opus-4-7') and historical backlog/design docs untouched.

Out of scope: effort default (stays max), any other flag defaults, the model enum/validation (orchestrator does not whitelist model strings).

Verification: uv run pytest skills/ralph-run/tests/ passes; uv run pyright skills/ralph-run/scripts passes; uv run ruff check . clean; grep -rn 'opus-4-7' on skills/ (excluding docstrings + backlog/design) returns no matches.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-run/scripts/ralph/args.py --model default is 'claude-opus-4-8'
- [x] #2 skills/ralph-run/SKILL.md defaults table model row and the divergence note both read claude-opus-4-8
- [x] #3 test_orchestrator_args.py default-model assertion expects claude-opus-4-8 and passes
- [x] #4 All explicit model='claude-opus-4-7' fixture inputs/assertions in skills/ralph-run/tests/ are updated to claude-opus-4-8 (no live 4-7 references remain outside docstrings and backlog/design history)
- [x] #5 uv run pytest skills/ralph-run/tests/ passes; uv run pyright skills/ralph-run/scripts passes; uv run ruff check . clean
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Update ralph-run orchestrator default model from claude-opus-4-7 to claude-opus-4-8 in args.py:81, SKILL.md (defaults table + divergence note), test_orchestrator_args.py:78 assertion, and 7 test fixture inputs/assertions across the test suite. Keep docstring example in tools/claude.py:60 and historical backlog/design docs untouched. Verify via pytest, pyright, ruff, and grep sweep.

Commit: `c6fba40` - task-179: Default Ralph model to Opus 4.8 (claude-opus-4-8)

All 5 ACs satisfied: orchestrator default flipped to claude-opus-4-8 (args.py:81), SKILL.md defaults table + divergence note both updated, test_orchestrator_args.py default assertion flipped, and the 7 fixture-input-only tests + test_tool_claude.py input/assertion all updated. Docstring example at tools/claude.py:60 and historical backlog/design docs deliberately left untouched per task scope. grep -rn 'opus-4-7' skills/ returns only that one docstring line. uv run pytest skills/ralph-run/tests/ → 185 passed; uv run pyright skills/ralph-run/scripts → 0 errors; uv run ruff check . → clean. Reviewer APPROVED.
<!-- SECTION:NOTES:END -->
