---
id: TASK-10
title: Remove Amp tool support
status: To Do
assignee: []
created_date: '2026-04-18 12:19'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Strip all Amp-related code, configuration, and documentation from the project. The project only supports Claude Code and opencode going forward. Remove Amp as default tool, Amp CLI references, Amp skill installation instructions, and prompt.md (Amp-specific prompt file).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh: Remove amp from tool choices, amp-specific prompt building, and TOOL default. Default tool becomes claude
- [ ] #2 README.md: Remove all Amp references, Amp skill installation instructions, and Amp usage examples
- [ ] #3 skills/ralph-init/SKILL.md: Remove Amp as AI tool option and Amp skill copy instructions
- [ ] #4 prompt.md: Delete file (Amp-specific prompt template)
- [ ] #5 All existing tests updated to reflect Amp removal and still pass
<!-- AC:END -->
