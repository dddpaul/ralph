---
id: TASK-245
title: Correct the stale devcontainer .claude architecture in doc-1
status: Done
assignee: []
created_date: '2026-09-27 12:58'
updated_date: '2026-09-27 13:33'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Backlog doc `doc-1` (Ralph Loop Comparative Research) still describes a devcontainer architecture that TASK-239/240/241 deleted. Two stale passages, verified at v0.6.4:

- **line ~369** — claims a volume overlay at the container-side `.claude` path, populated from a read-only bind of the host copy via postCreateCommand, and calls that overlay the source of the recurring drift bug (4 recurrences: TASK-137/139/141/142).
- **line ~465** — repeats that the volume overlay "has caused 4 recurrences of state drift".

Current reality: there is no such volume and no read-only host-copy bind. Instead:

- the project `.claude` directory is the shared workspace bind (no copy, no drift);
- a single-file bind overlays only `.claude/settings.local.json`, sourced from `.devcontainer/container-settings.local.json`;
- the user's home `.claude` is bound twice — once at the container user's home path and once at its own host path — so plugin registries resolve on both machines;
- `CLAUDE_CONFIG_DIR` points at the host path, which is what keeps registry entries host-shaped.

## Scope

Keep the historical incident record — the drift bug genuinely happened — but mark it resolved and name the resolving tasks. Do NOT rewrite the surrounding comparative-research analysis; this is a factual correction to the architecture description only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 doc-1 no longer asserts a live volume overlay at the container .claude path, and grep for workspace-host-claude across backlog/docs returns 0 hits
- [x] #2 doc-1 names the current mount set: shared workspace .claude bind, single-file settings.local.json overlay, dual home .claude bind, and CLAUDE_CONFIG_DIR at the host path
- [x] #3 The TASK-137/139/141/142 drift history is retained and explicitly marked resolved, naming TASK-239/240/241 as the resolving tasks
- [x] #4 git diff on doc-1 touches only the .claude architecture passages, leaving the comparative-research analysis unchanged
- [x] #5 The task-validator hook passes on the edited doc
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: rewrite doc-1 §4.6 Mounts bullet (line ~369) to the current mount set (workspace .claude bind, single-file settings.local.json overlay from .devcontainer/container-settings.local.json, dual home .claude bind, CLAUDE_CONFIG_DIR at host path) and mark the TASK-137/139/141/142 drift resolved by TASK-239/240/241; do the same for the §6.3 'Today' line (~465). Leave §0 key recommendation and §6.3 'Why' analysis untouched per Scope.

Rewrote doc-1 §4.6 Mounts bullet to the current mount set and added a 'History (resolved)' bullet naming TASK-137/139/141/142 drift and TASK-239/240/241 as the fix; corrected the §6.3 'Today' line likewise. §0 key recommendation and §6.3 'Why' bullet left untouched per Scope (they still read 'volume-overlay drift' — candidate for a follow-up reword). AC#5: task-validator.sh validates task files only; it passed on this task's edits. task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
