---
id: TASK-182
title: >-
  Fix utc-to-moscow quoted $HOME invocation in ralph-status SKILL (parallel to
  TASK-180)
status: Done
assignee: []
created_date: '2026-07-01 13:56'
updated_date: '2026-07-01 17:42'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-180. skills/ralph-status/SKILL.md line ~67 invokes the utc-to-moscow.sh helper QUOTED on its $HOME branch: `moscow_time=$(bash "$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh" "$utc_iso")`. The `"` right after `bash ` makes the literal command string differ from the seeded unquoted $HOME-form allow rule (Bash(bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)) -> permission prompt on the manual /ralph-status flow. TASK-180 fixed the identical bug in ralph-status-watch Rule (e) but was scoped to that file only; this is the sibling occurrence on the separate /ralph-status code path. Fix = unquote the path in the bash invocation (keep the [ -x "$HOME/..." ] test quoted and keep "$utc_iso" quoted), exactly as TASK-180 did for ralph-status-watch.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-status/SKILL.md $HOME branch invokes utc-to-moscow.sh WITHOUT quotes around the path: bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh "$utc_iso" (relative ./ and absolute branches unchanged; [ -x ... ] test stays quoted)
- [x] #2 grep for a quoted bash "$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh" invocation in skills/ralph-status/SKILL.md returns nothing
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Remove quotes around $HOME path in the bash invocation on line 67 of skills/ralph-status/SKILL.md (bash $HOME/.claude/.../utc-to-moscow.sh "$utc_iso"), exactly mirroring TASK-180's fix to ralph-status-watch Rule (e). Keep the [ -x "$HOME/..." ] test quoted (line 66), keep ./ and absolute branches unchanged, keep "$utc_iso" quoted. Verify with grep + ruff + pytest.

Commit: `ade4e37` - task-182: Unquote $HOME path in utc-to-moscow.sh invocation in ralph-status SKILL

Done: Unquoted the $HOME path in the utc-to-moscow.sh bash invocation at skills/ralph-status/SKILL.md:67 (bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh "$utc_iso"), mirroring TASK-180's ralph-status-watch fix. [ -x "$HOME/..." ] test stays quoted (line 66); ./ branch unchanged (line 65); "$utc_iso" stays quoted. No ralph-init template counterpart (R11 N/A). Gates: ruff clean, 185 pytest passed. task-reviewer APPROVED.
<!-- SECTION:NOTES:END -->
