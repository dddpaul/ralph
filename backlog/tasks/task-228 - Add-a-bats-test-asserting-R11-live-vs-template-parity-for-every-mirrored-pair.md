---
id: TASK-228
title: Add a bats test asserting R11 live-vs-template parity for every mirrored pair
status: To Do
assignee: []
created_date: '2026-09-03 20:45'
labels:
  - 'feature:task-filename-length-guard'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The task-reviewer caught template drift in TASK-227: `plugins/ralph/skills/ralph-init/templates/claude/hooks/naming-guard.sh` was mirrored from an intermediate version of `.claude/hooks/naming-guard.sh` and shipped a copy that failed this repo's own test suite. Nothing automated catches that class of defect — a grep over `tests/` finds no parity assertion for the R11 table in `.claude/task-reviewer-rules.md`.

Add a bats test (e.g. `tests/unit/template-parity.bats`) that walks the R11 live/template pairs and asserts each `diff` is silent. Pairs with documented carve-outs (`CLAUDE.md` generic section only; `.claude/task-reviewer-rules.md` excluded; `plugins/ralph/agents/*` excluded; `ralph.sh` / `refine.sh` shim-to-template only) need the carve-out encoded rather than skipped wholesale.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/unit/template-parity.bats exists and is picked up by 'bats tests/unit/'
- [ ] #2 The test fails when any live/template pair in the R11 table diverges (verified by mutating one template copy)
- [ ] #3 R11 carve-outs (CLAUDE.md generic-section-only, task-reviewer-rules.md, plugins/ralph/agents/) are encoded in the test rather than the whole pair being skipped
- [ ] #4 The test passes on master with no source changes
<!-- AC:END -->
