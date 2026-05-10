---
id: TASK-116
title: Add 'What next?' hand-off prompt to ralph-task skill
status: Done
assignee: []
created_date: '2026-05-10 19:09'
updated_date: '2026-05-10 19:23'
labels:
  - 'feature:ralph-task'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After `backlog task create` returns a new ID and the mandatory self-check passes, the skill currently proceeds without asking the user how to handle the new task — leading to silent defaults to interactive implementation. Add a 4-option AskUserQuestion hand-off prompt so the user explicitly picks: interactive now / Ralph now (autonomous loop) / continue chatting / other (freeform).

Source of truth for the design: `design/ralph-task-brainstorm.md` — see the 'Addendum: "What next?" hand-off (added 2026-05-10)' section near the bottom of the file. The addendum specifies the 4-option block, action mapping table, skip-condition table, and defensive defaults.

Witnessed defect: TASK-115 (init-firewall fix) was branched + implemented interactively without asking. User feedback: 'why do you start task interactive? i'd prefer ralph run later. or better — you should ask with options'. The fix lives in the skill (not auto-memory) so it's enforced uniformly.

Bootstrap note: this task is created BEFORE the skill carries the new section, so the very first 'What next?' prompt will fire after this task itself is created — same bootstrap pattern as the original skill build.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-task/SKILL.md contains a new section titled 'What next? (after create)' inserted between the 'Mandatory self-check (after create)' section and the 'Editing existing tasks (judgment moments)' section
- [x] #2 The new section documents the 4-option AskUserQuestion block with question stem 'Task TASK-<id> created. What next?', header 'What next?', and the four labels: 'Interactive now', 'Ralph now', 'Continue chatting', 'Other' — matching the table in design/ralph-task-brainstorm.md addendum
- [x] #3 The new section documents the multi-task variant: question stem switches to 'Tasks TASK-<id1>, TASK-<id2>, ... created. What next?' and option 2 description switches to '/ralph-run tasks=<id1>,<id2>,... watch=5m'
- [x] #4 The new section documents the action mapping: option 1 -> branch + CLAUDE.md Task Lifecycle steps 2-6; option 2 -> invoke '/ralph-run tasks=<id> watch=5m devcontainer=true'; option 3 -> no-op acknowledgment; option 4 -> one clarifying question then act, fall back to option 3 on persistent ambiguity
- [x] #5 The new section documents the skip-condition table: unambiguous execution-mode verbs in the trigger turn ('start it' / 'implement' / 'fix it now' -> option 1; 'ralph it' / 'run with ralph' / 'автономно' -> option 2; 'for later' / 'just log it' / 'на потом' -> option 3) bypass the prompt
- [x] #6 The new section documents defensive defaults: AskUserQuestion failure falls back to option 3 (never silently launches Ralph or branches); 'devcontainer=true' is passed explicitly to /ralph-run; the edit-deliberation lane (split / add-as-AC / rework) does NOT fire the prompt
- [x] #7 skills/ralph-task/SKILL.md 'Checklist before stopping' section gains two new bullets: '[ ] After create: AskUserQuestion fired unless skip-condition matched' and '[ ] Acted on the chosen option (1/2/3/4)'
- [x] #8 ~/.claude/projects/-Users-paul-Private-Projects-ai-ralph/memory/feedback_ask_before_implementing_new_tasks.md is deleted, and its line is removed from MEMORY.md (verifiable: ls returns 'No such file' and grep on MEMORY.md returns no match)
- [x] #9 After merge, running 'bash .claude/skills/ralph-sync/sync.sh classify' on skills/ralph-task/SKILL.md shows the file as needing sync; after running the sync, the same command shows it as [unchanged]
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Insert new 'What next? (after create)' section in skills/ralph-task/SKILL.md between Mandatory self-check and Editing existing tasks. Document 4-option AskUserQuestion block, multi-task variant, action mapping, skip conditions, defensive defaults. 2) Add 2 bullets to Checklist before stopping. 3) Delete ~/.claude/projects/-Users-paul-Private-Projects-ai-ralph/memory/feedback_ask_before_implementing_new_tasks.md and remove its MEMORY.md line. 4) Verify ralph-sync classify reports the file as needing sync. 5) Spawn task-reviewer agent on git diff master..HEAD before marking Done.

Commit: `53acfa0` - task-116: Add 'What next? (after create)' section to ralph-task skill

Implemented: skills/ralph-task/SKILL.md now carries the 'What next? (after create)' section (4-option AskUserQuestion block + multi-task variant + skip-condition table + defensive defaults). Closing checklist gained two bullets. Side effects: deleted auto-memory feedback file feedback_ask_before_implementing_new_tasks.md and removed its MEMORY.md line — rule lives in the skill from now on. Verified ralph-sync flow: classify [updated] → apply → classify [unchanged]. task-reviewer agent: APPROVED.
<!-- SECTION:NOTES:END -->
