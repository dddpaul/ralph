---
id: TASK-10
title: Remove Amp tool support
status: Done
assignee:
  - '@claude'
created_date: '2026-04-18 12:19'
updated_date: '2026-04-18 18:21'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Strip all Amp-related code, configuration, and documentation from the project. The project only supports Claude Code and opencode going forward. Remove Amp as default tool, Amp CLI references, Amp skill installation instructions, and prompt.md (Amp-specific prompt file).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph.sh: Remove amp from tool choices, amp-specific prompt building, and TOOL default. Default tool becomes claude
- [x] #2 README.md: Remove all Amp references, Amp skill installation instructions, and Amp usage examples
- [x] #3 skills/ralph-init/SKILL.md: Remove Amp as AI tool option and Amp skill copy instructions
- [x] #4 prompt.md: Delete file (Amp-specific prompt template)
- [x] #5 All existing tests updated to reflect Amp removal and still pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) ralph.sh: Remove amp from tool validation, remove amp prompt building branch, change default TOOL to claude. 2) README.md: Remove Amp references, installation, config, and links. 3) skills/ralph-init/SKILL.md: Remove Amp from tool question and usage examples. 4) prompt.md: Delete file. 5) Tests: Update argument-validation.bats to remove amp tests, update defaults to claude. Update common.bash comment. 6) AGENTS.md: Remove Amp references. 7) templates/ralph.sh: Same changes as main ralph.sh.

Commit: `e8673a1` - task-10: Remove Amp tool support, default to Claude Code

Removed all Amp references from ralph.sh, README.md, AGENTS.md, skills/ralph-init/SKILL.md, skills/ralph-run/SKILL.md, templates/ralph.sh, tests. Deleted prompt.md. Default tool changed from amp to claude. Test 99 (e2e backlog_workflow) is a pre-existing failure unrelated to this change.
<!-- SECTION:NOTES:END -->
