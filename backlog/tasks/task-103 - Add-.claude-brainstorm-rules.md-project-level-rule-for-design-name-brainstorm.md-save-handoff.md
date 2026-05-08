---
id: TASK-103
title: >-
  Add .claude/brainstorm-rules.md project-level rule for
  design/<name>-brainstorm.md save handoff
status: Done
assignee: []
created_date: '2026-05-08 19:05'
updated_date: '2026-05-08 19:20'
labels:
  - 'feature:ralph-review'
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
brainstorm is a third-party plugin (umputun-cc-thingz) we cannot modify. Mechanism for saving conversational design conclusions to disk uses brainstorm's project-level custom rules file: .claude/brainstorm-rules.md (loaded by brainstorm's resolve-rules.sh).

Add a rule that, before Phase 4 options, proposes saving design conclusions to design/<name>-brainstorm.md with this structure:
- Architecture decision (what was chosen, briefly)
- Components / flows (bullet list)
- Scope cuts (what we explicitly excluded and why)
- Open questions (anything deferred)
- Hand-off (next: ralph-prd to formalize as PRD, then ralph-backlog)

The existing user-global Phase 4 rule ('Create backlog task first') stays — both apply (project rules supplement, do not replace).

The rule must NOT modify brainstorm skill files (per brainstorm's CRITICAL constraint). Only writes to .claude/brainstorm-rules.md in the current repo.

Out of scope: ralph-prd path change (TASK-102), ralph-reviewer agent (separate).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .claude/brainstorm-rules.md exists and is non-empty in this repo
- [x] #2 Rule text instructs brainstorm to propose saving design conclusions to design/<name>-brainstorm.md before Phase 4 options
- [x] #3 Rule defines the brainstorm doc structure: Architecture decision, Components/flows, Scope cuts, Open questions, Hand-off
- [x] #4 Rule clarifies it supplements (does not replace) the existing Phase 4 'Create backlog task first' user-global rule
- [x] #5 Rule explicitly notes <name> must be kebab-case and shared with the eventual PRD slug
- [x] #6 Manual smoke verification: invoke brainstorm with a fake topic; confirm the loaded rule mentions design/<name>-brainstorm.md (read brainstorm's resolve-rules.sh output)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add project-level rule to existing .claude/brainstorm-rules.md. Insert a new section BEFORE the existing Phase 4 Override that instructs brainstorm to propose saving design conclusions to design/<name>-brainstorm.md. Keep existing Phase 4 Override intact. Rule defines the doc structure per AC#3, notes kebab-case naming per AC#5, and clarifies supplement relationship per AC#4.

Commit: `5fc39b9` - task-103: Add project-level brainstorm rule for design/<name>-brainstorm.md save handoff

Implemented project-level brainstorm rule in .claude/brainstorm-rules.md. Added Save Design Conclusions section before Phase 4 that proposes writing design/<name>-brainstorm.md with kebab-case naming. Preserved existing Phase 4 Override rule. Added .gitignore exclusion to track the file. Smoke-tested via resolve-rules.sh. Reviewer approved.
<!-- SECTION:NOTES:END -->
