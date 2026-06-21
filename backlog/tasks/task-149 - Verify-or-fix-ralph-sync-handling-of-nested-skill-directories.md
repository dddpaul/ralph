---
id: TASK-149
title: Verify or fix ralph-sync handling of nested skill directories
status: To Do
assignee: []
created_date: '2026-06-21 13:07'
labels:
  - 'feature:ralph-python-refactor'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-000 from design/ralph-python-refactor-prd.md (precondition for the Python orchestrator port).

The Python implementation introduces a nested `ralph/` package subdirectory and a `tests/` directory under `skills/ralph-run/scripts/`. The existing `.claude/skills/ralph-sync/sync.sh` must propagate these nested directories to `~/.claude/skills/ralph-run/scripts/` correctly. If sync.sh drops directories (e.g. uses non-recursive copy), fix it before US-001 can land.

Spec source: `.claude/skills/ralph-sync/sync.sh` (the script to test and potentially patch).

Outcome (recorded in --append-notes after the spike): one of (a) sync.sh handles nested directories as-is — no change needed; (b) sync.sh needed a fix — describe the change.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Spike: create throwaway directory `skills/ralph-run/scripts/spike/dummy.txt`
- [ ] #2 Run `/ralph-sync classify` and confirm classify output detects the new path
- [ ] #3 Run `/ralph-sync apply` and confirm `~/.claude/skills/ralph-run/scripts/spike/dummy.txt` exists after apply
- [ ] #4 If sync drops nested directories: patch `.claude/skills/ralph-sync/sync.sh` and re-verify both classify and apply work
- [ ] #5 Spike directory `skills/ralph-run/scripts/spike/` deleted before task is marked Done
- [ ] #6 Append-notes records outcome: works-as-is OR fix-applied (with description of the fix)
<!-- AC:END -->
