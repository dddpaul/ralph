---
id: TASK-111
title: Document label-lookup limitation in ralph-backlog skill
status: To Do
assignee: []
created_date: '2026-05-09 06:15'
updated_date: '2026-05-09 06:52'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
skills/ralph-backlog/SKILL.md mandates -l "feature:<name>" on every backlog task create call but does not tell the reader how to look those tasks up later. The natural answer (backlog task list -l <label>) does not work in backlog.md v1.44.0. Add a brief 'Looking up tasks by feature label' subsection (or note block) that cross-references the grep-based lookup pipeline documented in ralph-review's Step 2b. Do NOT duplicate the full pipeline — ralph-review remains the single source of truth for the workaround. The existing -l "feature:<name>" emission rule on backlog task create must be preserved unchanged. Update both the repo copy and the user-global copy via ralph-sync after merge.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 skills/ralph-backlog/SKILL.md contains a new subsection (or note block) explaining that 'backlog task list' does NOT support label filtering as of backlog.md v1.44.0
- [ ] #2 The note cross-references the lookup pipeline location (e.g. "see skills/ralph-review/SKILL.md Step 2b for the grep-based lookup pattern")
- [ ] #3 The existing -l "feature:<name>" emission rule on 'backlog task create' is preserved unchanged
- [ ] #4 ralph-sync classifies the project copy as [updated] after commit
<!-- AC:END -->
