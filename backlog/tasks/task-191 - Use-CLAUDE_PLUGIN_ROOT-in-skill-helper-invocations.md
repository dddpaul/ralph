---
id: TASK-191
title: Use CLAUDE_PLUGIN_ROOT in skill helper invocations
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 11:48'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-188
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Repoint skill helper-script invocations from HOME/.claude/skills to the CLAUDE_PLUGIN_ROOT plugin root so they resolve after plugin install. No allow-rule is needed because sandbox auto-allow covers the helpers. See design/ralph-marketplace-prd.md US-005.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-run invokes bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-run/scripts/preflight.sh and the matching wait-heartbeat.sh
- [x] #2 ralph-status and ralph-status-watch invoke bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-status/scripts/utc-to-moscow.sh
- [x] #3 The verbatim-literal-HOME allow-rule guidance is removed from those SKILL.md files
- [x] #4 No HOME/.claude/skills/ helper paths remain in the moved skills
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Repoint helper invocations to ${CLAUDE_PLUGIN_ROOT} in 3 moved SKILL.md files.
- ralph-run/SKILL.md L79,L82 (preflight.sh) + L119,L122 (wait-heartbeat.sh): repoint path $HOME/.claude/skills -> ${CLAUDE_PLUGIN_ROOT}/skills; drop 'type verbatim, literal unquoted $HOME' + 'matches seeded Bash(...) rule' allow-rule guidance (AC#1,#3).
- ralph-status/SKILL.md L63 + ralph-status-watch/SKILL.md L73 (utc-to-moscow.sh): repoint path (AC#2).
Out of scope: ralph-init perm-seeding refs (TASK-193/US-007); ralph-run L66 orchestrator ~/.claude path (TASK-190 resolver, non-helper). Verify AC#4 by grep for $HOME/.claude/skills helper paths in the 3 skills.

Commit: `add7f00` - task-191: Repoint skill helper invocations to ${CLAUDE_PLUGIN_ROOT}

Repointed helper invocations to ${CLAUDE_PLUGIN_ROOT} in ralph-run (preflight.sh, wait-heartbeat.sh), ralph-status and ralph-status-watch (utc-to-moscow.sh). Removed the verbatim/literal-$HOME + seeded-allow-rule guidance from ralph-run. ralph-init perm-seeding refs left for TASK-193 (US-007); ralph-run L66 orchestrator ~/.claude path is the TASK-190 resolver (non-helper), out of scope. Gate: ruff clean, 185 pytest pass. task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
