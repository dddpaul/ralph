---
id: TASK-181
title: >-
  Add universal Implementation Mode Gate (ask Ralph vs interactive before any
  task implementation)
status: Done
assignee: []
created_date: '2026-07-01 13:52'
updated_date: '2026-07-01 14:18'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Interactive sessions currently only ask execution-mode in ralph-task's post-create block and the handoff gate. Add a universal gate: before implementing ANY backlog task (named/selected/created/handoff), ask via AskUserQuestion 'How to run?' — Ralph (Recommended, first) or Interactive — unless the user's message already names the mode. Carve-outs: MODE: autonomous never asks; mechanical/edit ops are not implementation. Supersedes and reorders ralph-task's What-next block so Ralph is default/first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CLAUDE.md gains an Implementation Mode Gate rule: ask Ralph(Recommended)/Interactive before implementing any task in an interactive session
- [x] #2 Gate skips only when the user's message already names the mode; bare 'implement TASK-N'/'start it'/'go' must ask
- [x] #3 Rule explicitly exempts MODE: autonomous runs and mechanical/edit-deliberation ops
- [x] #4 skills/ralph-init/templates/root/CLAUDE.md mirrors the same gate rule
- [x] #5 skills/ralph-task/SKILL.md What-next block reordered so Ralph is option 1 '(Recommended)' and the two gates agree on the default
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add a universal '## Implementation Mode Gate' section between '## Autonomous Mode' and '## Task Lifecycle' in (1) /workspace/CLAUDE.md and (2) skills/ralph-init/templates/root/CLAUDE.md (byte-identical generic text for R11 parity). Rule: interactive sessions ask AskUserQuestion Ralph(Recommended, option1)/Interactive(option2) before branching/implementing ANY task (named/selected/created/handoff); skip ONLY when the user already names the mode; bare 'implement TASK-N'/'start it'/'go' must ask; carve-outs: MODE: autonomous never asks, mechanical/edit-deliberation ops never ask. Reorder skills/ralph-task/SKILL.md What-next 4-option block so Ralph is option1 (Recommended), Interactive option2; reconcile its skip table so bare implement/start verbs fire the prompt (Ralph default) to agree with the universal gate. Verify R11 parity + pytest/ruff green.

Commit: `aaa0a10` - task-181: Add universal Implementation Mode Gate (Ralph vs interactive) to CLAUDE.md + template; reorder ralph-task What-next so Ralph is default

Implemented: added byte-identical '## Implementation Mode Gate' section to CLAUDE.md and skills/ralph-init/templates/root/CLAUDE.md (interactive sessions ask Ralph(Recommended, opt1)/Interactive(opt2) before branching/implementing any task; skip only when user names the mode; bare implement/start/go must ask; carve-outs for MODE: autonomous and mechanical/edit-deliberation ops). Reordered skills/ralph-task/SKILL.md What-next block (Ralph=opt1 Recommended), reconciled Multi-task variant + skip table numbering, and added cross-reference so both gates default to Ralph. Reviewer APPROVED (R11 parity byte-identical, R12 consistent). Gates: ruff clean, 185 pytest passed.
<!-- SECTION:NOTES:END -->
