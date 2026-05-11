---
id: TASK-117
title: 'Increase ralph-review cumulative diff cap from 50,000 to 100,000 chars'
status: In Progress
assignee: []
created_date: '2026-05-11 07:05'
updated_date: '2026-05-11 07:08'
labels:
  - 'feature:ralph-review'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The cumulative diff limit in `skills/ralph-review/SKILL.md` Step 3c is currently 50,000 characters, which truncates many cross-task feature reviews and produces incomplete intent-to-implementation matrices. Raise to 100,000.

Two literal references in the same file (both must be updated):

```
skills/ralph-review/SKILL.md:159: 'If the diff exceeds 50,000 characters, truncate and append'
skills/ralph-review/SKILL.md:162: '[WARN: Diff truncated at 50,000 chars. Review may be incomplete.]'
```

After the edit, run ralph-sync to push to ~/.claude/skills/ralph-review/SKILL.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-review/SKILL.md Step 3c sentence reads 'If the diff exceeds 100,000 characters, truncate and append' (was 50,000)
- [x] #2 skills/ralph-review/SKILL.md truncation warning text reads '[WARN: Diff truncated at 100,000 chars. Review may be incomplete.]' (was 50,000)
- [x] #3 grep -n '50,000\|50000' skills/ralph-review/SKILL.md returns no matches
- [ ] #4 After merge, bash .claude/skills/ralph-sync/sync.sh classify shows skill ralph-review as [unchanged] (post-sync)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Edit applied: skills/ralph-review/SKILL.md lines 159 and 162 updated from 50,000 to 100,000. Verified via grep (no remaining 50,000 references).
<!-- SECTION:NOTES:END -->
