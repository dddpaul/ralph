---
id: TASK-124
title: Exempt /tmp writes from master-branch-guard and allowlist Write(/tmp/**)
status: In Progress
assignee: []
created_date: '2026-05-17 08:38'
updated_date: '2026-05-17 08:57'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When working on master and writing throwaway scratch files to /tmp (test scripts, scratch JSON, temp diagnostics), the master-branch-guard hook in .claude/hooks/master-branch-guard.sh blocks the Write/Edit tool call with 'BLOCKED: no active task branch'. /tmp is by definition ephemeral and not part of any commit, so requiring a task branch for it is friction with no safety value.

Also: Claude Code may prompt for permission on each Write(/tmp/...) call. Allowlist the pattern so /tmp writes are silent.

## What

Two surfaces:

### Hook exemption (R11 parity — both copies must match)

Add /tmp exemptions to the master-branch-guard hook alongside the existing design/ exemption:

```bash
case "$path" in /tmp/*|/private/tmp/*) exit 0;; esac
```

(/private/tmp covers macOS realpath; /tmp covers the literal form Claude tools usually pass.)

Files:
- `.claude/hooks/master-branch-guard.sh` — live project copy
- `skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` — template, byte-for-byte identical

### Permission allowlist

Add `Write(/tmp/**)` and `Edit(/tmp/**)` to the permissions.allow array in both:

- `.claude/settings.local.json` — live project copy
- `skills/ralph-init/templates/claude/settings.local.json` — template (so new Ralph projects also bypass the prompt)

## Source files / line refs

- .claude/hooks/master-branch-guard.sh line 12 (existing design/ exemption); add new case right after
- skills/ralph-init/templates/claude/hooks/master-branch-guard.sh (mirror)
- .claude/settings.local.json permissions.allow array
- skills/ralph-init/templates/claude/settings.local.json permissions.allow array

## Scope

Hook + permission only. No new scripts. No SKILL.md changes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .claude/hooks/master-branch-guard.sh contains a case branch matching '/tmp/*|/private/tmp/*' that exits 0 (placed alongside or immediately after the existing design/ exemption on line 12)
- [x] #2 skills/ralph-init/templates/claude/hooks/master-branch-guard.sh is byte-for-byte identical to the live .claude/hooks/master-branch-guard.sh (R11 parity)
- [x] #3 .claude/settings.local.json permissions.allow array contains both 'Write(/tmp/**)' and 'Edit(/tmp/**)'
- [x] #4 skills/ralph-init/templates/claude/settings.local.json permissions.allow array contains both 'Write(/tmp/**)' and 'Edit(/tmp/**)'
- [x] #5 Hook behavior verified by running 'echo {"tool_input":{"file_path":"/tmp/test.txt"}} | bash .claude/hooks/master-branch-guard.sh' on master — exits 0 with no JSON deny output
- [x] #6 Hook behavior verified by running the same with file_path=/Users/paul/Private/Projects/ai/ralph/src/foo.txt — still emits the BLOCKED deny JSON (negative test)
- [x] #7 bash -n on both .claude/hooks/master-branch-guard.sh copies passes
- [ ] #8 After merge, bash .claude/skills/ralph-sync/sync.sh classify shows skill ralph-init as [unchanged] (post-sync)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation: master-branch-guard.sh gains '/tmp/*|/private/tmp/*' exemption alongside design/ (both live + template, R11 parity verified by diff). settings.local.json adds Write(/tmp/**) + Edit(/tmp/**) in both live + template. Behavior verified by branch-stripped hook test: /tmp paths exit 0 silently, src/ paths emit BLOCKED, design/ still passes (no regression).
<!-- SECTION:NOTES:END -->
