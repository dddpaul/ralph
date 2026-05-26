---
id: TASK-132
title: Add ralph-handoff skill for cross-project Ralph task handoff
status: In Progress
assignee: []
created_date: '2026-05-26 17:43'
updated_date: '2026-05-26 17:54'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enable users planning an epic in source project A to deposit a self-contained backlog task into destination project B (which also runs Ralph + backlog), so B's Ralph loop can pick it up after a human confirmation gate. Mirrors mattpocock's handoff skill in spirit but uses the backlog CLI in destination CWD as the transport (which auto-allocates the destination-side task ID, avoiding any cross-project numbering conflicts). The skill is invoked from source; the destination-side responsibility is just to read the new task and run a validation checklist before starting work.

Design decisions locked during brainstorm:
- Status on creation: `To Do` (user confirmed Ralph isn't running idle when they handoff, so no race).
- Pure SKILL.md (no helper scripts) — V1 lean.
- AskUserQuestion fallback for fields not derivable from the source conversation.
- `Source: <abs-path>@<commit-sha>` line appended to notes for traceability.
- Skill does NOT commit the created task file — user decides.
- Lives at skills/ralph-handoff/ (picked up by ralph-sync automatically; no hardcoded list to edit).
- ralph-init advertises it in Next steps AND adds destination-side guidance to the CLAUDE.md template (Handoff Inbox section).
- No source-side audit doc written.

Out of scope: source-side audit doc, helper script, supporting status other than `To Do`, automatic git commit, two-way sync of completed status back to source.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-handoff/SKILL.md exists with frontmatter (name: ralph-handoff, description containing triggers like 'ralph handoff', 'handoff task', 'cross-project task', 'handoff to ralph project')
- [x] #2 SKILL.md instructs the source Claude to validate destination path has backlog/ directory and backlog CLI is runnable in that directory before proceeding
- [x] #3 SKILL.md instructs source Claude to read destination's README.md and CLAUDE.md (if present) to mirror its conventions/labels/AC style
- [x] #4 SKILL.md gathers required fields (title, why, AC bullets, destination-frame file paths, out-of-scope, dependencies, labels, priority) — using AskUserQuestion only for fields not derivable from the source conversation
- [x] #5 SKILL.md creates the task via (cd <dest-abs-path> && backlog task create ...) with status 'To Do' so destination's backlog CLI allocates the task ID
- [x] #6 The created task's description or append-notes contains: a Why section, the AC list, a 'Source: <abs-path-to-source-repo>@<commit-sha>' line, and a 'Before starting' validation checklist for destination Claude (verify paths exist, AC testable, deps met; STOP and ask user if unclear)
- [x] #7 Skill prints the assigned TASK-NNN, the destination project path, and the verbatim magic phrase: 'check new task TASK-NNN — do you understand, can you run it?' for the user to paste into destination Claude
- [x] #8 Skill explicitly does NOT git-add or git-commit the new task file in the destination repo — that decision is left to the user
- [x] #9 skills/ralph-init/SKILL.md Step 4 'Next steps' lists /ralph-handoff as a way to send a planned task to another Ralph project
- [x] #10 skills/ralph-init/templates/root/CLAUDE.md includes a 'Handoff Inbox' section instructing destination-side Ralph: tasks containing a 'Source:' line are inbound handoffs — run the validation checklist before starting; STOP and ask the user if anything is unclear
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Write skills/ralph-handoff/SKILL.md — pure markdown skill, frontmatter + 6 steps (preflight, recon destination, gather fields, compose, create task in dest CWD, print magic phrase).
2. Update skills/ralph-init/SKILL.md Step 4 Next steps section to advertise /ralph-handoff.
3. Update skills/ralph-init/templates/root/CLAUDE.md — add a 'Handoff Inbox' section so destination-side Ralph validates Source: handoffs.
4. Spawn task-reviewer agent on the diff.
5. Mark Done; commit; merge.
<!-- SECTION:NOTES:END -->
