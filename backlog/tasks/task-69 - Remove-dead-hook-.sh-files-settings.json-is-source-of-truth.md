---
id: TASK-69
title: Remove dead hook .sh files; settings.json is source of truth
status: Done
assignee: []
created_date: '2026-05-01 05:59'
updated_date: '2026-05-01 06:03'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After TASK-66, hook logic lives inline inside .claude/settings.json. The 6 files in .claude/hooks/*.sh are reference-only copies that the runtime never executes — they are dead code that can drift out of sync with the inline versions (this already happened: TASK-67 fixed both, but if a future fix lands inline only, the .sh files become stale).

## Scope

1. Delete .claude/hooks/ directory (all 6 .sh files).
2. Update .gitignore: remove the negation patterns for .claude/hooks/ (lines 21-22 of root .gitignore: \!.claude/hooks/ and \!.claude/hooks/**) since the dir no longer exists.
3. Verify settings.json is the single source of truth — no references to .claude/hooks/ paths remain.
4. Update skills/ralph-init/SKILL.md if it mentions hook scripts (it should not — section 3.7 only writes settings.json + task-reviewer.md).
5. Add a brief comment-or-doc explaining that hook logic is intentionally inlined into settings.json (location TBD — could be top of settings.json if comments are supported, otherwise a note in CLAUDE.md or AGENTS.md). Subtask: confirm whether settings.json supports JSONC-style comments before placing the note inline.

## Out of scope
Switching to the alternative 'separate scripts as source of truth' design (option b from the brainstorm). That is a separate decision that, if chosen later, would supersede this cleanup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Directory .claude/hooks/ removed entirely
- [x] #2 Root .gitignore no longer contains negation patterns for .claude/hooks/
- [x] #3 settings.json contains no references to .claude/hooks/ paths
- [x] #4 All 6 PreToolUse hooks still function correctly after the cleanup (smoke test: trigger one hook, e.g. a forbidden commit, verify it blocks)
- [x] #5 skills/ralph-init/SKILL.md is consistent with the new layout (no mention of distributing hook scripts)
- [x] #6 A short note documents that hook logic is inlined in settings.json (placement: top-of-file comment if JSONC is supported, else a line in AGENTS.md or CLAUDE.md)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Pre-research finding (2026-04-30): Claude Code settings.json is strict JSON — no // or /* */ comments, no trailing commas. Open feature requests #29370 and #17968 exist but unshipped. Therefore AC6's note about hook-logic-being-inlined must live in CLAUDE.md or AGENTS.md, NOT inline in settings.json. The _comment key convention is unofficial and discouraged.

Plan: 1) Delete .claude/hooks/ directory. 2) Remove negation patterns from .gitignore lines 21-22. 3) Verify settings.json has no .claude/hooks/ references (confirmed: none). 4) SKILL.md already clean (confirmed). 5) Add note to AGENTS.md about hooks being inlined in settings.json. 6) Smoke test a hook. 7) Commit.

Commit: `7ad45e3` - task-69: Remove dead hook .sh files; settings.json is source of truth

All 6 .sh hook files deleted, .gitignore cleaned, AGENTS.md updated. Smoke test confirmed inline hooks still work. Code review approved.
<!-- SECTION:NOTES:END -->
