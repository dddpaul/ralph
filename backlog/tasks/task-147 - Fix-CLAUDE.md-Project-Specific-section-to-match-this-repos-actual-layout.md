---
id: TASK-147
title: Fix CLAUDE.md Project-Specific section to match this repo's actual layout
status: In Progress
assignee: []
created_date: '2026-06-21 10:35'
updated_date: '2026-06-21 10:35'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CLAUDE.md line 91 claims 'Plugin layout: skills live under plugins/<domain>/skills/<name>/ — not at repo root' and references '.claude-plugin/marketplace.json'. This is wrong for this repo: skills live at skills/<name>/ (e.g., skills/ralph-run/SKILL.md), there is no .claude-plugin/marketplace.json, and this repo is not a Claude Code plugin marketplace — it's a Ralph workflow repo that propagates skills to ~/.claude/ via the ralph-sync skill. The misleading paragraph appears to have been pasted from a different project template. Replace it with an accurate description of this repo's actual layout.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CLAUDE.md no longer claims skills live under plugins/<domain>/skills/<name>/
- [x] #2 CLAUDE.md no longer references .claude-plugin/marketplace.json (which does not exist in this repo)
- [x] #3 CLAUDE.md Project-Specific section accurately describes this repo: skills at skills/<name>/, propagated to ~/.claude/ via ralph-sync, R11 template parity with skills/ralph-init/templates/
- [x] #4 ls .claude-plugin/ 2>/dev/null returns nothing (verifies the removed claim was genuinely absent)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Replaced lines 86-91 of CLAUDE.md. Plugin-marketplace references removed; replaced with accurate description of this repo (skills at skills/<name>/, agents at agents/<name>.md, ralph-sync propagation, R11 template parity). Also broadened Language from 'Python (with Markdown for skill documentation)' to 'Bash + Markdown today; Python is the target for new orchestration code per the uv-only conventions below' since the orchestrator and hooks are still bash. Added shell-script R5 reference to the Lint line.
<!-- SECTION:NOTES:END -->
