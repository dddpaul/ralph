---
id: TASK-16
title: Disable backlog remote_operations by default in ralph-init skill
status: Done
assignee:
  - '@claude'
created_date: '2026-04-19 08:09'
updated_date: '2026-04-19 08:21'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When ralph-init bootstraps a new project via 'backlog init', the backlog config defaults to remote_operations=true which causes 'git fetch' on every CLI call, leading to SSH passphrase prompts. Fix: in skills/ralph-init/SKILL.md section 3.5, add 'backlog config set remoteOperations false' immediately after 'backlog init'. Add a one-sentence comment explaining why (avoids SSH prompts on each CLI call).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/SKILL.md section 3.5 contains 'backlog config set remoteOperations false' command after 'backlog init'
- [x] #2 A short explanation is included for why remoteOperations is disabled
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add 'backlog config set remoteOperations false' command in section 3.5 right after the 'backlog init' command, with a brief explanation about avoiding SSH prompts.

Commit: `94b6e69` - task-16: Disable backlog remoteOperations in ralph-init skill

Added 'backlog config set remoteOperations false' to skills/ralph-init/SKILL.md section 3.5 after backlog init command. Inline comment explains the reason.
<!-- SECTION:NOTES:END -->
