---
id: TASK-93
title: >-
  Allowlist echo and date in settings.local.json so /ralph-status compound call
  no longer prompts
status: In Progress
assignee: []
created_date: '2026-05-03 07:24'
updated_date: '2026-05-03 07:25'
labels:
  - permissions
  - settings
  - ralph-status
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The /ralph-status SKILL Step 1 mandates a single compound Bash call:

  stat -f %m backlog/.ralph-heartbeat ... ; echo "---" ; date +%s ; echo "---" ; backlog task list --plain

Components: stat, echo, date, backlog task list. Current allowlist has Bash(stat:*) and Bash(backlog task list:*) but is missing Bash(echo:*) and Bash(date:*). Compound commands prompt when ANY component lacks permission, so the SKILL triggers an approval prompt every time even though every component is read-only.

This stopped working transparently after TASK-77/79/85 narrowed the allowlist (broader rules used to cover it). Add the two missing entries — both are zero-risk read-only.

Mirror to skills/ralph-init/templates/claude/settings.local.json per R11 (template parity).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Add 'Bash(echo:*)' and 'Bash(date:*)' to .claude/settings.local.json permissions.allow
- [x] #2 Mirror the two entries to skills/ralph-init/templates/claude/settings.local.json (R11 template parity); diff -q on the two files post-edit shows them differing only in the non-permissions sections that already differed before (or being byte-identical if they were before)
- [x] #3 Verify the SKILL's compound call would no longer prompt: with the new allowlist, all four components (stat, echo, date, backlog task list) match an allowlist entry
- [ ] #4 task-reviewer (subagent_type=task-reviewer) returns APPROVED on git diff master..HEAD
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added 'Bash(date:*)' and 'Bash(echo:*)' to both .claude/settings.local.json (project) and skills/ralph-init/templates/claude/settings.local.json (template). Compound /ralph-status call now matches all four components: Bash(stat:*), Bash(echo:*), Bash(date:*), Bash(backlog task list:*). 

Scope-creep cleanup also done in same edit (project file only): removed redundant 'Bash(echo "exit=0")' literal-match (now covered by Bash(echo:*)) and dropped a stray trailing-comma JSON syntax issue. Template was clean already.
<!-- SECTION:NOTES:END -->
