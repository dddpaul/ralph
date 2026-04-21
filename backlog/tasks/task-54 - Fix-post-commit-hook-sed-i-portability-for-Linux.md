---
id: TASK-54
title: Fix post-commit hook sed -i portability for Linux
status: Done
assignee:
  - '@claude'
created_date: '2026-04-21 18:33'
updated_date: '2026-04-21 18:37'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Post-commit hook line 32 uses sed -i '' which is macOS BSD sed only. GNU sed (Linux/devcontainer) requires sed -i without empty string. Use temp file approach instead: sed 's/...' file > file.tmp && mv file.tmp file
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Post-commit hook works on both macOS and Linux
- [x] #2 Amend detection and hash replacement still works
- [x] #3 Template post-commit hook in ralph-init also updated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Replace sed -i '' on line 32 with a portable temp-file approach (sed > .tmp && mv .tmp original). Apply same fix to both .git/hooks/post-commit and skills/ralph-init/templates/post-commit.

Commit: `e277a57` - task-54: Portable sed in post-commit hook using temp file

Replaced macOS-only sed -i '' with portable temp-file approach in both .git/hooks/post-commit and skills/ralph-init/templates/post-commit. Files changed: skills/ralph-init/templates/post-commit (tracked), .git/hooks/post-commit (local hook).
<!-- SECTION:NOTES:END -->
