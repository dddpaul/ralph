---
id: TASK-62
title: Add upgrade mode to ralph-init skill
status: Done
assignee:
  - '@claude'
created_date: '2026-04-25 16:27'
updated_date: '2026-04-25 17:34'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-init currently skips all existing files (skip-if-exists pattern), which means running it on a project with older ralph files leaves stale versions in place. Add an `## Upgrade Mode` section to SKILL.md (separate from init flow, not inline conditionals) with steps U1-U5.

**U1 — Preflight:** Same as Step 1, plus verify ralph was previously initialized (ralph.sh or CLAUDE.md must exist).

**U2 — Build File Status Table:** Compare each managed file against its template. Categories: current / outdated / missing / skipped.
Files to check:
- ralph.sh → exact match against templates/ralph.sh
- CLAUDE.md → compare only lines ABOVE `## Project-Specific` heading against template (everything from `## Project-Specific` down is the project block and must be preserved, including conventions)
- .git/hooks/post-commit → exact match against templates/post-commit
- .claude/settings.local.json → exact match against templates/settings.local.json
- .devcontainer/devcontainer.json → exact match, skip if no .devcontainer/ dir
- .devcontainer/init-firewall.sh → exact match, skip if no .devcontainer/ dir
- .devcontainer/Dockerfile → always skip (assembled, cannot diff meaningfully)
- .gitignore → skip (already has append-only logic in init flow)

**U3 — Present Batch Summary:** Show table with file + status. For outdated files: ralph.sh and post-commit get plain language summary of what changed; settings.local.json gets unified diff shown (project may have custom permissions). Then ask: Update all outdated files? Or list files to skip. User replies yes/all, skip <file>, or none/cancel.

**U4 — Apply Updates:**
- ralph.sh, post-commit: overwrite from template, chmod +x
- settings.local.json: overwrite from template
- devcontainer.json, init-firewall.sh: overwrite from template
- CLAUDE.md (special): (1) read existing file, (2) find `## Project-Specific` line, (3) extract from that line to EOF as project block, (4) read template, (5) take everything above `## Project-Specific` from template as generic block, (6) write generic block + project block
- Missing files: create from template same as init flow

**U5 — Summary:** Print which files were updated / current / skipped (user choice) / N/A (not present).

**Trigger update:** Update skill description to also trigger on: upgrade ralph, ralph upgrade, update ralph files.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Skill detects --upgrade flag (or 'upgrade ralph' / 'update ralph files') and switches to upgrade flow
- [x] #2 Each managed file is compared against its template version (exact match for most, above-Project-Specific for CLAUDE.md)
- [x] #3 Outdated files: ralph.sh and post-commit get plain language change summary; settings.local.json gets unified diff
- [x] #4 User is presented batch summary and can approve all or name files to skip
- [x] #5 CLAUDE.md upgrade preserves everything from ## Project-Specific heading down (including conventions)
- [x] #6 Summary shows which files were updated, current, skipped by user, or not applicable
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add an ## Upgrade Mode section after Step 4 in SKILL.md with steps U1-U5. U1: preflight (same as Step 1 + verify ralph was previously initialized). U2: build file status table comparing managed files against templates (exact match for most, above-Project-Specific for CLAUDE.md). U3: present batch summary with plain language summaries for ralph.sh/post-commit and unified diff for settings.local.json. U4: apply updates with CLAUDE.md special merge logic. U5: print summary. Also update skill description/triggers. The upgrade section is self-contained, no changes to the init flow.

Commit: `872c287` - task-62: Upgrade mode for ralph-init skill

Implemented: Added ## Upgrade Mode section to SKILL.md with steps U1-U5 (preflight, file status table, batch summary with details, apply updates with CLAUDE.md merge logic, summary). Updated skill description triggers to include upgrade/update phrases. Files changed: skills/ralph-init/SKILL.md.
<!-- SECTION:NOTES:END -->
