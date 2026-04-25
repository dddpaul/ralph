---
id: TASK-63
title: Fix preflight.sh path resolution in ralph-run skill
status: Done
assignee:
  - '@claude'
created_date: '2026-04-25 17:11'
updated_date: '2026-04-25 17:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
SKILL.md Step 3 hardcodes `bash skills/ralph-run/scripts/preflight.sh` as a relative path from the ralph repo root. When the skill runs in another project, the script doesn't exist at that path — fails with exit code 127. Fix: instruct Claude to resolve the script path relative to where SKILL.md lives (same pattern as ralph-init's `templates/` directory reference). Also update the Bash allow entry in both settings.local.json files to match the new invocation pattern.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SKILL.md Step 3 resolves preflight.sh relative to the skill directory, not project CWD
- [x] #2 ralph-run works when invoked from a project that is not the ralph repo
- [x] #3 Bash allow entries in settings.local.json files match the updated invocation
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Update SKILL.md Step 3 to instruct Claude to locate preflight.sh in the scripts/ directory next to SKILL.md (same pattern as ralph-init's templates/ reference), then pass the resolved absolute path to bash. (2) Update Bash allow entry in skills/ralph-init/templates/settings.local.json — change from hardcoded path to a wildcard pattern matching any preflight.sh path. (3) Update .claude/settings.local.json similarly. The key insight: Claude reads SKILL.md and knows its location, so it can resolve scripts/preflight.sh relative to the skill directory and pass the full path to Bash.

Commit: `d96b6d8` - task-63: Fix preflight.sh path resolution for cross-project use

Fixed preflight.sh path resolution. SKILL.md Step 3 now instructs Claude to resolve scripts/preflight.sh relative to SKILL.md location (same pattern as ralph-init templates/). Updated Bash allow entry to wildcard `bash */preflight.sh:*` in both template and local settings.local.json. Files: skills/ralph-run/SKILL.md, skills/ralph-init/templates/settings.local.json, .claude/settings.local.json (local only).
<!-- SECTION:NOTES:END -->
