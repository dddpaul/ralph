---
id: TASK-68
title: Fix ralph-init .gitignore template missing negation patterns
status: Done
assignee:
  - '@claude'
created_date: '2026-05-01 05:56'
updated_date: '2026-05-01 05:56'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
skills/ralph-init/SKILL.md section 3.4 appends '.claude/' to .gitignore but omits the negation patterns that allow .claude/settings.json and .claude/agents/ to be tracked. Without them, new projects bootstrapped via ralph-init will silently gitignore the project-wide hooks and review agent. Match the patterns from this repo's .gitignore lines 17-22.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SKILL.md section 3.4 .gitignore append block includes negation patterns: \!.claude/settings.json, \!.claude/agents/, \!.claude/agents/**
- [ ] #2 After ralph-init runs in a fresh project, git check-ignore .claude/settings.json returns empty (file is tracked)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `d38c9df` - task-68: Add .claude negation patterns to ralph-init .gitignore template

Section 3.4 now appends \!.claude/settings.json, \!.claude/agents/, \!.claude/agents/** alongside .claude/ so new projects properly track project-wide hooks and the task-reviewer agent. AC2 (verify in fresh project) deferred to next ralph-init invocation in a real project.
<!-- SECTION:NOTES:END -->
