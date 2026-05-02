---
id: TASK-89
title: Refactor ralph-init templates folder by install destination
status: Done
assignee: []
created_date: '2026-05-02 17:22'
updated_date: '2026-05-02 17:26'
labels:
  - skill
  - ralph-init
  - refactor
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Group skills/ralph-init/templates/ flat layout (27 files in one folder) into subfolders that mirror install destinations. Refactor only — no filename changes, no behavioral changes, no template content edits.

New layout:
- root/ — files installed to repo root (ralph.sh, CLAUDE.md, CLAUDE.conventions.*.md)
- git-hooks/ — installed to .git/hooks/ (commit-msg, post-commit)
- claude/ — installed to .claude/ (settings.json, settings.local.json, agents/, hooks/)
- devcontainer/ — installed to .devcontainer/ (devcontainer.json, init-firewall.sh, Dockerfile.base, lang/<all-Dockerfile.lang.* and Dockerfile.install.*>)
- obsidian/ — unchanged

Update SKILL.md path references throughout (Step 3 init + U2/U4 upgrade).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All template files moved via 'git mv' to preserve history; filenames unchanged
- [x] #2 Folder structure matches the agreed layout (root/, git-hooks/, claude/, devcontainer/, obsidian/) with claude/agents/, claude/hooks/, devcontainer/lang/ subfolders
- [x] #3 skills/ralph-init/SKILL.md updated: every templates/<file> path reflects new location, in both Step 3 init and U2/U4 upgrade sections
- [x] #4 No filename renames; no content edits to any template file
- [x] #5 Visual inspection: 'find skills/ralph-init/templates -type f' shows 0 files at top level (other than what currently exists in obsidian/)
- [x] #6 task-reviewer (subagent_type=task-reviewer) returns APPROVED on git diff master..HEAD
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. git mv templates files into new subfolders (root/, git-hooks/, claude/{agents,hooks}/, devcontainer/lang/). Filenames unchanged.
2. Update SKILL.md path references in Step 3 (init) and U2/U4 (upgrade).
3. Verify with 'find templates -type f' that no stray files remain at top level.
4. Commit on task-89 branch.
5. Spawn task-reviewer agent for review.
6. Mark Done and merge.

Refactored skills/ralph-init/templates/ from flat 27-file layout into 5 subfolders mirroring install destinations: root/, git-hooks/, claude/{agents,hooks}/, devcontainer/lang/, obsidian/ (untouched). All filenames preserved; all moves via git mv (similarity index 100%). SKILL.md updated: every templates/<file> reference rewritten in Step 3 (init) and U2/U4 (upgrade). Reviewer (subagent_type=task-reviewer) APPROVED — all 6 ACs satisfied.

Commit: `90234a2` - task-89: Group ralph-init templates by install destination
<!-- SECTION:NOTES:END -->
