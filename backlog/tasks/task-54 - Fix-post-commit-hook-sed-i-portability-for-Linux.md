---
id: TASK-54
title: Fix post-commit hook sed -i portability for Linux
status: To Do
assignee: []
created_date: '2026-04-21 18:33'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Post-commit hook line 32 uses sed -i '' which is macOS BSD sed only. GNU sed (Linux/devcontainer) requires sed -i without empty string. Use temp file approach instead: sed 's/...' file > file.tmp && mv file.tmp file
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Post-commit hook works on both macOS and Linux
- [ ] #2 Amend detection and hash replacement still works
- [ ] #3 Template post-commit hook in ralph-init also updated
<!-- AC:END -->
