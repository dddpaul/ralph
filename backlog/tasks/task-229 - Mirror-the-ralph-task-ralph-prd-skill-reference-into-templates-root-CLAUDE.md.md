---
id: TASK-229
title: Mirror the ralph-task/ralph-prd skill reference into templates/root/CLAUDE.md
status: Done
assignee: []
created_date: '2026-09-04 04:44'
updated_date: '2026-09-04 06:03'
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
- [x] #1 templates/root/CLAUDE.md line for backlog CLI usage matches the live CLAUDE.md line byte-for-byte
- [x] #2 The DRIFT allow-list entry for it is removed from tests/unit/template-parity.bats and the test still passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Replace line 47 of plugins/ralph/skills/ralph-init/templates/root/CLAUDE.md with the live CLAUDE.md line 47 byte-for-byte (adds the ralph-task skill and ralph-prd -> ralph-backlog references; all three skills verified present under plugins/ralph/skills/ and bundled by the ralph plugin, so a bootstrapped project really does get them). (2) Delete DRIFT entries 3 and 4 from claude_md_allowed_deviations() in tests/unit/template-parity.bats and prune the matching numbered comment block, leaving only the two step-6 CARVE-OUT entries. The list's stale-entry guard means the deletion is mandatory, not cosmetic: leaving them in fails the test. (3) Verify with the bats suite (baseline on master: 163/163 green under LC_ALL=C). (4) Shipped plugins/ralph/** file changes, so .claude/hooks/bump-version.sh --auto must bump both manifests at merge time.

Commit: `3187ea6` - task-229: mirror the ralph-task/ralph-prd skill reference into the CLAUDE.md template

Mirrored the live CLAUDE.md backlog-CLI sentence (line 47) into plugins/ralph/skills/ralph-init/templates/root/CLAUDE.md byte-for-byte, and deleted the two DRIFT:TASK-229 rows plus their numbered comment entries from claude_md_allowed_deviations() in tests/unit/template-parity.bats. The allow-list now holds only the two step-6 plugin-governance CARVE-OUT rows, and the whole CLAUDE.md generic region is in parity apart from that one documented hunk.

Content check before mirroring: ralph-task, ralph-prd and ralph-backlog all exist under plugins/ralph/skills/ and are bundled by the ralph plugin, and the template already pointed at /ralph-run and /ralph-handoff, so the added sentence advertises skills a bootstrapped project actually receives (via /plugin install, not via ralph-init file copying).

Anti-vacuity proved by mutation rather than argument, both re-run independently by the reviewer: (A) reverting the template line to the pre-112 sentence fails test 2 with 'undocumented deviation in the CLAUDE.md generic region'; (B) re-adding the fixed sentence as an allow-list row fails test 2 with 'stale claude_md_allowed_deviations entry'. (B) is why the AC2 deletion was mandatory rather than cosmetic.

Gates: bats 163/163 (LC_ALL=C, matching the master baseline), uv run pytest 346 passed, uv run ruff check clean, no .py touched. task-reviewer: APPROVED.

Side observation, not fixed here (out of scope): claude_md_allowed_deviations() has a stale-entry guard but the sibling non_mirrored_templates() and repo_local_hooks() lists do not, so an obsolete exemption there would rot silently. Filed as a follow-up.

Commit: `3bf52d7` - task-229: bump plugin version to 0.4.1 (patch)
<!-- SECTION:NOTES:END -->
