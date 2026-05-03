---
id: TASK-94
title: >-
  Fix TASK-92 defects: restore frontmatter to agents/task-reviewer.md and remove
  stale .claude/agents/ leftover
status: Done
assignee: []
created_date: '2026-05-03 07:33'
updated_date: '2026-05-03 07:50'
labels:
  - agent
  - bug-fix
  - ralph-defect
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-92 (executed by Ralph) had two defects:

1. **agents/task-reviewer.md missing frontmatter.** Ralph stripped it during the move and rationalized: 'Agent file ships without YAML frontmatter in the repo — users add frontmatter when copying to ~/.claude/agents/.' That's wrong: users copy the file unchanged via 'cp'; the frontmatter must be IN the file. Also violates R3 in our own rules ('Any change that creates or modifies a file under agents/, .claude/agents/, or ~/.claude/agents/ MUST include valid YAML frontmatter').

2. **Stale user-global rules path inside agents/task-reviewer.md.** Lines 15-17 reference '~/.claude/agents/task-reviewer-rules.md' — TASK-91 moved that file to '~/.claude/task-reviewer-rules.md' (no agents/). Project tier on line 12 was correctly updated, but the user-global fallback wasn't.

3. **Stale on-disk .claude/agents/task-reviewer.md leftover.** TASK-92 successfully removed it from git (git ls-files confirms not tracked), but the file persists on disk because the macOS sandbox blocked an unlink during the rename. It's a working-tree ghost (R9 warns about exactly this). The .claude/agents/ directory should also be removed entirely.

The on-disk ghost actually contains the correct, up-to-date content (with frontmatter and correct rule paths) — Ralph should have moved this content as-is. Use it as the canonical source for the fix.

After the fix, Paul should refresh user-global: 'cp agents/task-reviewer.md ~/.claude/agents/' (his current ~/.claude/agents/task-reviewer.md still has the old TASK-91-era rules paths).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 agents/task-reviewer.md has YAML frontmatter (name: task-reviewer, description: ..., color: green) matching the canonical content from the on-disk ghost .claude/agents/task-reviewer.md
- [x] #2 agents/task-reviewer.md user-global fallback path (line ~22 inside the bash resolver) reads '~/.claude/task-reviewer-rules.md' (NOT '~/.claude/agents/task-reviewer-rules.md')
- [x] #3 On-disk .claude/agents/ directory is removed entirely (rm -rf) — no working-tree leftovers
- [x] #4 Verify: 'git ls-files .claude/agents/' returns nothing; 'ls .claude/agents/' fails with No such directory; 'head -5 agents/task-reviewer.md' shows YAML frontmatter
- [x] #5 task-reviewer (subagent_type=task-reviewer) returns APPROVED on git diff master..HEAD
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `31cc533` - task-94: Restore frontmatter to agents/task-reviewer.md; remove .claude/agents leftover

Re-reviewed at commit 31cc533 — task-reviewer APPROVED. Both TASK-92 defects fixed: frontmatter restored, stale rules path corrected, on-disk .claude/agents/ leftover removed.
<!-- SECTION:NOTES:END -->
