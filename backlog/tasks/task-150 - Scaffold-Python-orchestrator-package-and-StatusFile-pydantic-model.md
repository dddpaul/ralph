---
id: TASK-150
title: Scaffold Python orchestrator package and StatusFile pydantic model
status: Done
assignee: []
created_date: '2026-06-21 13:08'
updated_date: '2026-06-21 13:55'
labels:
  - 'feature:ralph-python-refactor'
dependencies:
  - TASK-149
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-001 from design/ralph-python-refactor-prd.md.

Foundational scaffold: PEP 723 entry point, sibling `ralph/` package, tests directory, pyright/ruff/pytest config at repo root, and the pydantic `StatusFile` model that produces byte-identical JSON output to today's bash writer.

Spec sources:
- `skills/ralph-run/scripts/ralph.sh` lines 200–450 (status-write code paths in bash)
- A sample `backlog/.ralph-status.json` from a recent bash run (use as golden fixture)
- All 18 fields and their semantics enumerated in design/ralph-python-refactor-prd.md §3 US-001 and §7 (historical-context appendix entries for the status schema)

Out of scope: orchestrator loop, subprocess management, signal parsing — those land in later tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Create `skills/ralph-run/scripts/ralph_orchestrator.py` with PEP 723 inline metadata block (`requires-python = ">=3.14"`, `dependencies = ["pydantic>=2.5"]`)
- [x] #2 Create `skills/ralph-run/scripts/ralph/__init__.py` and `skills/ralph-run/scripts/ralph/status.py`
- [x] #3 `StatusFile` pydantic model defines all 18 fields matching today's bash schema (field names and types per PRD §7)
- [x] #4 `StatusFile.write_atomic(path)` uses tempfile.NamedTemporaryFile + os.replace() for atomic external-reader visibility
- [x] #5 Add golden-file round-trip test in `skills/ralph-run/tests/test_status.py`: load sample bash-output JSON, parse via pydantic, re-serialize, assert byte-equal to original
- [x] #6 Create `pyproject.toml` at repo root with `[tool.ruff]`, `[tool.pyright]`, and `[tool.pytest.ini_options]` sections (tool-config only — no `[project]` table)
- [x] #7 Spike confirmation: `import ralph` succeeds from `ralph_orchestrator.py` (PEP 723 + sibling package resolves via sys.path)
- [x] #8 `uv run pyright --strict skills/ralph-run/scripts` passes
- [x] #9 `uv run ruff check skills/ralph-run/scripts` passes
- [x] #10 `uv run pytest skills/ralph-run/tests/test_status.py` passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Create pyproject.toml at repo root with [tool.ruff], [tool.pyright], [tool.pytest.ini_options].
2. Update .gitignore to exclude .ruff_cache, .pyright, __pycache__, .pytest_cache.
3. Create skills/ralph-run/scripts/ralph_orchestrator.py with PEP 723 inline metadata, sys.path bootstrap so 'import ralph' resolves to sibling package.
4. Create skills/ralph-run/scripts/ralph/__init__.py and skills/ralph-run/scripts/ralph/status.py with pydantic StatusFile model: 21 fields (pid, started_at, state, iteration, max_iterations, tool, tasks_done, tasks_remaining, current_task, last_iteration_duration, elapsed, errors, completed_at, exit_code, iteration_started_at, timeout_sec, paused_reason, paused_buffer_min, paused_remaining_min, paused_block_end_time, paused_at). PRD says 18 but lists 21; go with the explicit field list per §3 US-001.
5. write_atomic(path) uses tempfile.NamedTemporaryFile(delete=False, dir=same parent) + os.replace().
6. JSON shape: single-line compact JSON (no spaces between separators) to match bash output. Use model_dump_json with sort_keys False; ensure field declaration order matches bash key order.
7. Create skills/ralph-run/tests/test_status.py with golden-file roundtrip against captured backlog/.ralph-status.json.
8. Verify pyright --strict, ruff, pytest all pass.

Implementation complete.

**Files added:**
- pyproject.toml (repo root): [tool.uv], [dependency-groups] dev, [tool.ruff], [tool.pyright], [tool.pytest.ini_options]. Uses PEP 735 dependency-groups for dev tools without [project] table (PRD non-goal).
- .python-version: pins Python 3.14 for uv.
- .gitignore: added Python tooling caches (__pycache__, .pytest_cache, .ruff_cache, .pyright_cache, .venv).
- skills/ralph-run/scripts/ralph_orchestrator.py: PEP 723 entry-point with sys.path bootstrap. Prints 'ralph.status.StatusFile import OK' as the spike verification.
- skills/ralph-run/scripts/ralph/__init__.py
- skills/ralph-run/scripts/ralph/status.py: ErrorEntry + StatusFile pydantic models, field declaration order matches bash output exactly. write_atomic() uses NamedTemporaryFile + os.replace.
- skills/ralph-run/tests/fixtures/{status_running,status_completed,status_paused,status_with_errors}.json: 4 golden fixtures.
- skills/ralph-run/tests/test_status.py: parametrized roundtrip across all 4 fixtures + write_atomic tests + extra-field rejection test (8 tests total).

**Verification:**
- uv run pyright skills/ralph-run/scripts → 0 errors (strict mode via pyproject [tool.pyright] strict = [...])
- uv run ruff check skills/ralph-run/scripts → All checks passed
- uv run pytest skills/ralph-run/tests/test_status.py → 8 passed
- uv run skills/ralph-run/scripts/ralph_orchestrator.py → exit 0, sibling-package import resolves via PEP 723.

**Notes for reviewer:**
- AC #3 says '18 fields' but the explicit field list in PRD §3 enumerates 21. Implementation matches the explicit list (21 fields).
- AC #8 says 'pyright --strict' but pyright 1.1.410 has no --strict CLI flag — strict mode is configured in pyproject.toml [tool.pyright] strict = ['skills/ralph-run/scripts']. Functional equivalent: 'uv run pyright skills/ralph-run/scripts' runs with strict checking.
- pydantic ConfigDict(extra='forbid') is used so the model rejects unknown fields — catches future schema drift between bash and Python writers.

Commit: `81fc07b` - task-150: Scaffold Python orchestrator package and StatusFile model

task-reviewer APPROVED. Final build+lint+tests pass: pyright 0 errors, ruff clean, pytest 8/8.
<!-- SECTION:NOTES:END -->
