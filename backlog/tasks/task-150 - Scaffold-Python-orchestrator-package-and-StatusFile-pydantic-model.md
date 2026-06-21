---
id: TASK-150
title: Scaffold Python orchestrator package and StatusFile pydantic model
status: To Do
assignee: []
created_date: '2026-06-21 13:08'
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
- [ ] #1 Create `skills/ralph-run/scripts/ralph_orchestrator.py` with PEP 723 inline metadata block (`requires-python = ">=3.14"`, `dependencies = ["pydantic>=2.5"]`)
- [ ] #2 Create `skills/ralph-run/scripts/ralph/__init__.py` and `skills/ralph-run/scripts/ralph/status.py`
- [ ] #3 `StatusFile` pydantic model defines all 18 fields matching today's bash schema (field names and types per PRD §7)
- [ ] #4 `StatusFile.write_atomic(path)` uses tempfile.NamedTemporaryFile + os.replace() for atomic external-reader visibility
- [ ] #5 Add golden-file round-trip test in `skills/ralph-run/tests/test_status.py`: load sample bash-output JSON, parse via pydantic, re-serialize, assert byte-equal to original
- [ ] #6 Create `pyproject.toml` at repo root with `[tool.ruff]`, `[tool.pyright]`, and `[tool.pytest.ini_options]` sections (tool-config only — no `[project]` table)
- [ ] #7 Spike confirmation: `import ralph` succeeds from `ralph_orchestrator.py` (PEP 723 + sibling package resolves via sys.path)
- [ ] #8 `uv run pyright --strict skills/ralph-run/scripts` passes
- [ ] #9 `uv run ruff check skills/ralph-run/scripts` passes
- [ ] #10 `uv run pytest skills/ralph-run/tests/test_status.py` passes
<!-- AC:END -->
