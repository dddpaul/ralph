---
id: TASK-83
title: Remove backlog-tasks Edit-blocking hook; replace with soft CLAUDE.md guidance
status: Done
assignee: []
created_date: '2026-05-01 17:56'
updated_date: '2026-05-01 18:32'
labels:
  - hook
  - task-management
  - cleanup
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The PreToolUse hook that blocks Edit tool calls on 'backlog/tasks/*.md' is too broad. It prevents all direct edits to task files even when the change is a surgical in-place text replacement that cannot break structural invariants. Concrete cost: small text fixes to long descriptions or AC lines force a full 'backlog task edit -d "<full description>"' replacement (no --append-description exists) or a remove-and-re-add dance for AC text fixes (the --acceptance-criteria flag appends instead of replacing). Both paths are slow, error-prone, and consume far more tokens than a 2-line Edit call.

## Pre-TASK-66 history

In CLAUDE.md immediately before TASK-66 (commit 6130b82^), the rule lived as a soft note in the 'Backlog CLI Reference' section:

  ### Backlog CLI Reference
  Use `backlog` CLI for all task operations. **Never edit task files directly.**

A nearby line (about --notes) had the same form:

  **Never use `--notes`** — it overwrites the Notes section, destroying commit hashes. Use `--append-notes` instead.

TASK-66 then lifted both soft rules into PreToolUse hooks: notes-guard.sh for `--notes`, and the Edit-block hook on backlog/tasks/*.md for direct edits.

## Why TASK-66 was right for `--notes` and wrong for direct edits

The two rules look symmetric but their false-positive profiles diverge sharply:

| Rule | Pre-66 form | Lifted to hook? | False positives |
|---|---|---|---|
| `--notes` overwrites Notes | "Never use `--notes`" | yes (notes-guard.sh) | Zero — `--notes` is *always* a destructive overwrite of Notes (which holds commit hashes from the post-commit hook). No legitimate use exists. |
| Edit task files directly | "Never edit task files directly" | yes (the hook in question) | High — most in-place text fixes are safe; the hook blocks them anyway, even when the diff stays within an existing line and touches neither frontmatter nor markers nor AC count. |

The original CLAUDE.md rule ("**Never** edit task files directly") was already overstated — written absolutely but with an implicit "...because most edits go through the CLI for good reasons". TASK-66 took the absolute wording at face value and converted it into a hard block. Result: every safe surgical edit is blocked along with the unsafe ones.

## Resolution

Option A from the brainstorm: remove the hook entirely. Replace with soft guidance in CLAUDE.md and the ralph-init template that documents the actual scope of the rule.

## Soft-guidance text to add to CLAUDE.md

Insert after the 'Use `backlog` CLI for all task operations' line in the Task Lifecycle section (or as a new 'Editing tasks' sub-section):

  Prefer 'backlog task edit' for: adding/removing acceptance criteria, status changes, dependency edits, label/priority changes, frontmatter changes, append-notes, and AC checkbox flips (--check-ac / --uncheck-ac). Direct Edit tool is fine for in-place text changes inside the description body or inside an existing AC's text — that is, any change whose diff stays within an existing line and does not touch frontmatter, section markers (<\!-- SECTION:... -->, <\!-- AC:... -->), or the count of AC lines.

Apply the same change to skills/ralph-init/templates/CLAUDE.md so future projects inherit the guidance.

## Out of scope

- Structural-corruption guard (option C from the brainstorm) — if direct edits actually do break files in practice, file a follow-up task to add a non-blocking PostToolUse warning.
- Other TASK-66 hooks — none of them are touched. This task narrows exactly one over-converted rule.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 PreToolUse hook entry that blocks Edit on 'backlog/tasks/*.md' is removed from .claude/settings.json
- [x] #2 Same hook entry is removed from skills/ralph-init/templates/settings.json so newly bootstrapped projects do not ship it
- [x] #3 CLAUDE.md gains a short 'Editing tasks' note (or extends the existing Task Lifecycle bullet) describing when to use 'backlog task edit' versus the Edit tool, per the resolution text in this task's description
- [x] #4 skills/ralph-init/templates/CLAUDE.md receives the same note in the same location so future projects inherit it
- [x] #5 Manual smoke test: invoke the Edit tool on a backlog/tasks/task-N - *.md file (text inside description body); the edit succeeds and is not blocked
- [x] #6 Manual smoke test: 'backlog task edit N --append-notes "..."' still works and the post-commit hook still appends commit hashes (existing behavior unchanged)
- [x] #7 Manual smoke test: 'backlog task edit N --check-ac M' still works (existing behavior unchanged)
- [x] #8 No other PreToolUse / PostToolUse hooks are removed by this task — only the 'backlog/tasks/.*\.md' Edit-block entry
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Remove the backlog/tasks Edit-block hook entry from .claude/settings.json (line 43-44). 2) Remove the same entry from skills/ralph-init/templates/settings.json (line 43-44). 3) Add soft guidance note to CLAUDE.md Task Lifecycle section. 4) Add same note to templates/CLAUDE.md. 5) Smoke tests. 6) Commit and review.

AC#6 smoke test: --append-notes works

Commit: `7ba81d5` - task-83: Remove backlog-tasks Edit-blocking hook, add soft CLAUDE.md guidance

Commit: `26b5d4c` - task-83: Restore original printf syntax in ASCII-validation hooks

All ACs verified. Code review approved. Hook removed from both settings files, soft guidance added to both CLAUDE.md files.
<!-- SECTION:NOTES:END -->
