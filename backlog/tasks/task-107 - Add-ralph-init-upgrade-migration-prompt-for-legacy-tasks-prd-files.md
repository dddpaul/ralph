---
id: TASK-107
title: Add ralph-init upgrade migration prompt for legacy tasks/prd-* files
status: To Do
assignee: []
created_date: '2026-05-08 19:06'
labels:
  - 'feature:ralph-review'
dependencies:
  - TASK-102
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-init upgrade flow currently doesn't know about the design/ convention. Projects that ran ralph-prd before TASK-102 have their PRDs at tasks/prd-<name>.md; running ralph-init upgrade after TASK-102 leaves them stranded.

Add a migration step to skills/ralph-init/SKILL.md upgrade flow (and the user-global copy via ralph-sync):

When entering upgrade mode:
1. Detect any files matching tasks/prd-*.md (glob).
2. For each, propose: 'Detected legacy PRD at tasks/prd-<name>.md. Move to design/<name>-prd.md? [y/N]'
3. On y: git mv (preserves history), output 'moved'. On N: leave alone, output 'skipped (user)'.
4. Idempotent: if no tasks/prd-*.md files exist, the migration step says nothing.

Same logic for tasks/brainstorm-*.md if any exist (unlikely but safe to handle).

The migration step must fit cleanly into the existing upgrade flow's status table, OR appear as a separate 'Legacy file migration' section before the main batch summary. Implementer's choice; document in the task notes which placement was chosen.

Out of scope: ralph-prd path change (TASK-102), other upgrade-flow file additions, brainstorm rules file.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph-init upgrade flow detects tasks/prd-*.md files and proposes moving each to design/<name>-prd.md (suffix style)
- [ ] #2 User can decline per-file with N; declined files are left alone, not deleted
- [ ] #3 Move uses 'git mv' (not raw mv) to preserve history
- [ ] #4 Migration is idempotent: no-op when no legacy files exist
- [ ] #5 Migration also handles tasks/brainstorm-*.md files in the same way
- [ ] #6 Template parity (R11): skills/ralph-init/SKILL.md is the user-global skill, not in the project-template parity table — verify no ralph-init/templates/ files need a corresponding change
<!-- AC:END -->
