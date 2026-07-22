---
id: TASK-201
title: Scaffold ralph/refine Python sub-package and entrypoint
status: To Do
assignee: []
created_date: '2026-07-22 16:29'
labels:
  - 'feature:ralph-refine'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-001 of ralph-refine. Create the ralph/refine/ sub-package plus a refine_orchestrator.py entrypoint so the refine loop runs as Python under the shared toolchain. See backlog doc-4 (ralph-refine Overview) for cross-task invariants and design/ralph-refine-prd.md US-001.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 plugins/ralph/skills/ralph-run/scripts/ralph/refine/__init__.py exists and the package imports ralph.tools, ralph.devcontainer, ralph.signals without error
- [ ] #2 plugins/ralph/skills/ralph-run/scripts/refine_orchestrator.py exists, mirrors ralph_orchestrator.py (PEP-723 header, inserts its dir into sys.path), and dispatches into ralph.refine.cli:main
- [ ] #3 refine_orchestrator.py --help prints usage and exits 0
- [ ] #4 pyright strict passes on ralph/refine/
- [ ] #5 uv run ruff check . passes
<!-- AC:END -->
