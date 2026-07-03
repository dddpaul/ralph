---
id: TASK-194
title: Delete the ralph-sync skill
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 15:35'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-188
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remove ralph-sync since plugin install and directory-source replace its distribution job. See design/ralph-marketplace-prd.md US-008.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The .claude/skills/ralph-sync/ directory (SKILL.md and sync.sh) is deleted
- [x] #2 No references to ralph-sync remain in CLAUDE.md, README, or other skills outside backlog/archive and design/
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) git rm .claude/skills/ralph-sync/{SKILL.md,sync.sh} [AC#1]. (2) CLAUDE.md L107: surgically drop the ralph-sync propagation sentence only; leave skill-layout paths + 'NOT a marketplace' line to TASK-196/US-010. (3) README.md L34: drop the /ralph-sync updating mechanism; leave full install rewrite to TASK-196/US-010. (4) Verified other skills already grep-clean. Out of scope for this task (named AC = CLAUDE.md/README/skills): ralph.sh comments + task-reviewer-rules.md R11 carve-out are TASK-195/US-009 (R11 parity); brainstorm-rules.md example bullet is not a skill/CLAUDE.md/README.

Commit: `3760e96` - task-194: Delete ralph-sync skill and drop CLAUDE.md and README references

Done: deleted .claude/skills/ralph-sync/ (SKILL.md + sync.sh); surgically removed ralph-sync refs from CLAUDE.md L107 and README L34. Named-scope grep (CLAUDE.md/README/all SKILL.md) clean. task-reviewer APPROVED (impl commit 3760e96). Gate: ruff clean, 185 pytest pass. Deferred by design: ralph.sh + task-reviewer-rules.md R11 refs -> TASK-195; README install rewrite + CLAUDE.md path/marketplace flip -> TASK-196.
<!-- SECTION:NOTES:END -->
