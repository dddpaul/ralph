---
id: TASK-62
title: Add upgrade mode to ralph-init skill
status: To Do
assignee: []
created_date: '2026-04-25 16:27'
updated_date: '2026-04-25 17:07'
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
- [ ] #1 Skill detects --upgrade flag (or 'upgrade ralph' / 'update ralph files') and switches to upgrade flow
- [ ] #2 Each managed file is compared against its template version (exact match for most, above-Project-Specific for CLAUDE.md)
- [ ] #3 Outdated files: ralph.sh and post-commit get plain language change summary; settings.local.json gets unified diff
- [ ] #4 User is presented batch summary and can approve all or name files to skip
- [ ] #5 CLAUDE.md upgrade preserves everything from ## Project-Specific heading down (including conventions)
- [ ] #6 Summary shows which files were updated, current, skipped by user, or not applicable
<!-- AC:END -->
