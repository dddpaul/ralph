---
id: TASK-196
title: Update documentation for the marketplace
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 16:06'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-188
  - TASK-190
  - TASK-194
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update README and CLAUDE.md for plugin install and the new layout. See design/ralph-marketplace-prd.md US-010.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README install section uses /plugin marketplace add and /plugin install ralph@dddpaul-ralph instead of cp -r skills/* into ~/.claude/skills
- [x] #2 README architecture paths point at plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py
- [x] #3 CLAUDE.md skill-layout paths are updated and the NOT a Claude Code plugin marketplace line is flipped to describe the marketplace, with ralph-sync references removed
- [x] #4 uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (AC1) Replace README skills-install 'cp -r skills/* ~/.claude/skills/' (First-time setup + Setup Option 2) with '/plugin marketplace add dddpaul/ralph' + '/plugin install ralph@dddpaul-ralph'; opencode manual-copy path repointed to plugins/ralph/skills/. (AC2) Reprefix README Key-Files table, Shim/Canonical-Orchestrator section, and Python-test paths skills/ralph-* -> plugins/ralph/skills/ralph-*; orchestrator now bundled by ralph plugin at plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py. (AC3) CLAUDE.md Project-Specific lines 106-107: reprefix skill-layout+R11-template paths to plugins/ralph/skills/...; flip 'NOT a Claude Code plugin marketplace' to describe the dddpaul-ralph marketplace; ralph-sync already absent from README/CLAUDE.md. (AC4) uv run ruff check . (baseline already green). Edits confined to CLAUDE.md ## Project-Specific section -> no R11 template-parity drift.

Commit: `ce35f45` - task-196: Update README and CLAUDE.md for plugin marketplace install and plugins/ralph layout

Implemented (docs-only, README.md + CLAUDE.md). AC1: replaced 'cp -r skills/* ~/.claude/skills/' in First-time-setup and Setup Option 2 with '/plugin marketplace add dddpaul/ralph' + '/plugin install ralph@dddpaul-ralph'; opencode manual-copy repointed to plugins/ralph/skills/ralph-*. AC2: reprefixed Key-Files table, Shim/Canonical-Orchestrator section (now bundled by the ralph plugin at plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py, with resolver-precedence note), and all Python-test paths skills/ralph-* -> plugins/ralph/skills/ralph-*; added marketplace.json + plugins/ralph rows. AC3: CLAUDE.md Project-Specific lines 106-107 skill-layout+R11-template paths reprefixed to plugins/ralph/skills/...; flipped 'NOT a Claude Code plugin marketplace' to describe the dddpaul-ralph marketplace + ralph plugin; ralph-sync already absent. AC4: uv run ruff check . -> All checks passed. Edits confined to CLAUDE.md ## Project-Specific section => no R11 template-parity drift (task-reviewer confirmed). Verify: 185 pytest passed; task-reviewer APPROVED.
<!-- SECTION:NOTES:END -->
