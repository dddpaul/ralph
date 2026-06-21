---
id: TASK-148
title: Fan out ralph-python-refactor PRD to 8 backlog tasks (US-000 to US-007)
status: In Progress
assignee: []
created_date: '2026-06-21 13:04'
updated_date: '2026-06-21 13:12'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Wrapper task to convert design/ralph-python-refactor-prd.md into 8 backlog tasks (one per user story) plus a backlog overview doc. Each child task carries the feature:ralph-python-refactor label and a dependency chain enforcing the migration order (sync spike → scaffold → helpers/internals (parallel) → claude subprocess → opencode + entry point + E2E → strangler + ralph-init mirror → cutover). Per the PRD's R16-spirit discipline, child tasks reference bash source line ranges as their spec, NOT historical task IDs in -d. The historical-context appendix lives in the PRD; child tasks point at the PRD by name.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 backlog overview doc created at backlog/docs/ describing the feature, tech stack, architecture, scope, and task dependency graph
- [x] #2 8 child tasks created in backlog/tasks/ (US-000 sync spike through US-007 cutover); each has feature:ralph-python-refactor label
- [x] #3 Dependency chain wired via --dep task-N flags matching the migration ordering DAG from the PRD
- [x] #4 Each child task description references design/ralph-python-refactor-prd.md as the spec source and includes the specific bash source line range(s) to port
- [x] #5 No child task description references any brainstorm file (R16); compliance verified by grep on backlog/tasks/
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fan-out complete.

Created backlog/docs/doc-2 (Ralph Python Refactor: Project Overview — navigation sheet pointing at design/ralph-python-refactor-prd.md as the spec).

Created 8 child tasks under feature:ralph-python-refactor label:
- TASK-149 (US-000) — ralph-sync nested-directory spike (precondition, no deps)
- TASK-150 (US-001) — scaffold + StatusFile pydantic contract (dep: 149)
- TASK-151 (US-002) — port preflight, wait-heartbeat, usage-check helpers (dep: 150; parallelizable with 152)
- TASK-152 (US-003) — port signals, tasks, heartbeat, usage, Tool ABC (dep: 150; parallelizable with 151)
- TASK-153 (US-004) — claude subprocess + process-group cleanup (dep: 151, 152)
- TASK-154 (US-005) — opencode + entry point + fake-claude E2E (dep: 153)
- TASK-155 (US-006) — strangler RALPH_IMPL dispatch + ralph-init R11 mirror (dep: 154)
- TASK-156 (US-007) — cutover + bash deletion + downstream upgrade path (dep: 155)

R16 grep clean across all 8: no design/*-brainstorm.md references in -d.
PRD reference present in all 8: each task cites design/ralph-python-refactor-prd.md as spec source.
Bash source line ranges quoted per task (per PRD §10 reviewer cross-check).

AC count per task: 6, 10, 9, 10, 11, 12, 10, 12 (typecheck/lint/pytest mechanical ACs included; product ACs land in 5–9 range each).
<!-- SECTION:NOTES:END -->
