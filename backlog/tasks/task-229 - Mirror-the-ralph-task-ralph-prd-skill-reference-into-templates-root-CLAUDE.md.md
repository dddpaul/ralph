---
id: TASK-229
title: Mirror the ralph-task/ralph-prd skill reference into templates/root/CLAUDE.md
status: To Do
assignee: []
created_date: '2026-09-04 04:44'
labels: []
dependencies:
  - TASK-228
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-228's new R11 parity test found pre-existing drift in the CLAUDE.md generic section: live line "Use \`backlog\` CLI for all task operations..." gained a reference to the `ralph-task` skill and the `ralph-prd` -> `ralph-backlog` flow in task-112, but plugins/ralph/skills/ralph-init/templates/root/CLAUDE.md still carries the pre-112 sentence. The skills ship in the ralph plugin, so a bootstrapped project should be told about them.

The parity test pins this deviation in its allow-list as DRIFT (not a carve-out). Fixing the template must also remove that allow-list entry, so the test starts enforcing parity for the line.

Note: touching a shipped plugins/ralph/** file requires a version bump (.claude/hooks/bump-version.sh --auto).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 templates/root/CLAUDE.md line for backlog CLI usage matches the live CLAUDE.md line byte-for-byte
- [ ] #2 The DRIFT allow-list entry for it is removed from tests/unit/template-parity.bats and the test still passes
<!-- AC:END -->
