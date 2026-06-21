---
id: TASK-149
title: Verify or fix ralph-sync handling of nested skill directories
status: In Progress
assignee: []
created_date: '2026-06-21 13:07'
updated_date: '2026-06-21 13:29'
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
- [x] #1 Spike: create throwaway directory `skills/ralph-run/scripts/spike/dummy.txt`
- [x] #2 Run `/ralph-sync classify` and confirm classify output detects the new path
- [x] #3 Run `/ralph-sync apply` and confirm `~/.claude/skills/ralph-run/scripts/spike/dummy.txt` exists after apply
- [x] #4 If sync drops nested directories: patch `.claude/skills/ralph-sync/sync.sh` and re-verify both classify and apply work
- [x] #5 Spike directory `skills/ralph-run/scripts/spike/` deleted before task is marked Done
- [x] #6 Append-notes records outcome: works-as-is OR fix-applied (with description of the fix)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
- Read .claude/skills/ralph-sync/sync.sh — classify uses 'diff -rq' (recursive, line 47); apply uses 'cp -r' (recursive, lines 115 + 120 via rm -rf; cp -r for updated skills).
- Prior is strong that nested directories work as-is. Still required to run the spike empirically per AC 1-3.
- Steps: (1) create skills/ralph-run/scripts/spike/dummy.txt; (2) run sync.sh classify, expect [updated] skill ralph-run; (3) run sync.sh apply with sandbox bypass (writes to ~/.claude/); (4) verify ~/.claude/skills/ralph-run/scripts/spike/dummy.txt exists; (5) delete source spike + re-apply to clean destination; (6) confirm destination spike gone.
- If any step fails: patch sync.sh and record fix in --append-notes.

Outcome: sync.sh handles nested skill directories correctly as-is — NO FIX NEEDED.

Empirical results:
- mkdir -p skills/ralph-run/scripts/spike/ && echo ... > spike/dummy.txt
- bash .claude/skills/ralph-sync/sync.sh classify → reported '[updated] skill ralph-run', exit 1 (changes detected)
- bash .claude/skills/ralph-sync/sync.sh apply → '[applied] skill ralph-run (updated)', Applied 1 item(s)
- ls ~/.claude/skills/ralph-run/scripts/spike/dummy.txt → present, 47 bytes (matches source byte-for-byte)
- rm -rf skills/ralph-run/scripts/spike/ + re-apply → destination spike directory removed cleanly

Mechanism: classify uses 'diff -rq' (recursive, sync.sh:47), apply uses 'cp -r' on new skills (sync.sh:115) and 'rm -rf dst; cp -r' on updated skills (sync.sh:119-120). Both are recursive by construction. The nested 'ralph/' package, 'tests/' directory, and any further subdirectories introduced by TASK-150 onward will propagate without any sync.sh change.

AC #4 is vacuously satisfied (no fix applied, so no fix to describe).

Implication for TASK-150: when the Python scaffold lands, '/ralph-sync classify' will detect ralph-run as [updated]; '/ralph-sync apply' will propagate the full scaffold (ralph_orchestrator.py + ralph/ package + tests/) to ~/.claude/skills/ralph-run/scripts/ atomically via the rm -rf + cp -r path.
<!-- SECTION:NOTES:END -->
