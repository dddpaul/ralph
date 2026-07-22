---
id: TASK-201
title: Scaffold ralph/refine Python sub-package and entrypoint
status: Done
assignee: []
created_date: '2026-07-22 16:29'
updated_date: '2026-07-22 16:48'
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
- [x] #1 plugins/ralph/skills/ralph-run/scripts/ralph/refine/__init__.py exists and the package imports ralph.tools, ralph.devcontainer, ralph.signals without error
- [x] #2 plugins/ralph/skills/ralph-run/scripts/refine_orchestrator.py exists, mirrors ralph_orchestrator.py (PEP-723 header, inserts its dir into sys.path), and dispatches into ralph.refine.cli:main
- [x] #3 refine_orchestrator.py --help prints usage and exits 0
- [x] #4 pyright strict passes on ralph/refine/
- [x] #5 uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan (US-001 scaffold): (1) Create ralph/refine/__init__.py re-exporting shared ralph.tools/devcontainer/signals via __all__ (smoke-imports the reused layer, AC#1). (2) Create ralph/refine/cli.py with typed build_parser()+main(argv) — argparse parser with prog=refine + description; --help exits 0 (AC#3). Full flag set deferred to TASK-202. (3) Create refine_orchestrator.py mirroring ralph_orchestrator.py: PEP-723 header (py>=3.14, pydantic), sys.path.insert of _HERE, dispatch to ralph.refine.cli:main (AC#2). Verify: import smoke, --help exit 0, uv run pyright on refine/ (AC#4), uv run ruff check . (AC#5), uv run pytest (no regressions). No test file — TASK-201 scope is scaffold only; US-002 adds test_refine_args.py.

Commit: `8b8afb4` - task-201: scaffold ralph/refine sub-package + refine_orchestrator.py entrypoint (US-001)

Done (US-001 scaffold). Implemented: ralph/refine/__init__.py (re-exports reused ralph.tools/devcontainer/signals via __all__ — single import site for the reused layer, smoke-tests reachability from the pinned root, AC#1); ralph/refine/cli.py (typed build_parser()+main(argv|None); --help prints usage & exits 0, AC#3; full flag set/validation deferred to TASK-202); refine_orchestrator.py (executable PEP-723 launcher mirroring ralph_orchestrator.py element-by-element — shebang, script header, sys.path pin of _HERE, noqa:E402 deferred import — dispatching into ralph.refine.cli:main, AC#2). Verified: import smoke OK; --help exit 0; pyright strict 0 errors on refine/ + orchestrator (AC#4); uv run ruff check . clean (AC#5, after isort auto-fix collapsed a double blank line to one); pytest 204 passed (no regressions). Reviewed by task-reviewer agent -> APPROVED (8-item checklist + R1-R16; reused-layer contract holds, no bespoke subprocess). Gotcha for next iterations: the .claude/hooks/commit-prefix-guard.sh sed only parses a single-line -m "..." message — multi-line -m leaves msg empty and the commit is blocked even with a correct task-N: prefix; use a one-line subject.
<!-- SECTION:NOTES:END -->
