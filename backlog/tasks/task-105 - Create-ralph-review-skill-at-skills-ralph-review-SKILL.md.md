---
id: TASK-105
title: Create /ralph-review skill at skills/ralph-review/SKILL.md
status: To Do
assignee: []
created_date: '2026-05-08 19:05'
labels:
  - 'feature:ralph-review'
dependencies:
  - TASK-104
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a user-global skill that orchestrates the cumulative feature review. Distributed via ralph-sync to ~/.claude/skills/ralph-review/.

Invocation: /ralph-review name=<name> [tasks=<N,M,K>]

Steps:
1. Pre-conditions:
   - At least one of design/<name>-prd.md or design/<name>-brainstorm.md exists. If neither → BLOCKED.
   - At least one in-scope task with status Done. Resolved via tasks= override OR by querying 'backlog task list -l feature:<name> -s Done --plain'. If empty → BLOCKED.
   - Diff range non-empty.
2. Determine diff <base>: walk in-scope task files, collect 'Commit:' hashes (post-commit hook appends these), pick earliest's parent.
3. Build agent input bundle: brainstorm doc + PRD + per-task summary (title, ACs, notes) + truncated git diff (filter by feature surface).
4. Spawn ralph-reviewer agent (subagent_type=ralph-reviewer) with the bundle and rubric prompt. Foreground.
5. Save full review output to design/<name>-review-<YYYY-MM-DD>.md. Append -01, -02 suffix if file exists (never overwrite).
6. Print verdict line + drift list to chat. Hint user about the saved file.

Error handling:
- Agent crash/timeout → 'review failed: <reason>', do not fabricate verdict
- Truncated diff → spawn agent in chunks, aggregate, surface WARN
- Missing brainstorm or PRD section → skip relevant passes, note in output

Out of scope: ralph-reviewer agent itself (TASK-104), README updates, migration prompt.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 skills/ralph-review/SKILL.md exists with valid YAML frontmatter and clear trigger keywords (ralph review, cumulative review, review feature)
- [ ] #2 Pre-conditions enforced: BLOCKED messages match the exact strings designed in Section 4
- [ ] #3 Tasks resolution supports both 'feature:<name>' label and explicit tasks= override (Approach D)
- [ ] #4 Diff base derivation reads 'Commit:' hashes from in-scope task files (not git log inference)
- [ ] #5 Output saved to design/<name>-review-<YYYY-MM-DD>.md with -NN suffix on collision (never overwrites)
- [ ] #6 Spawns ralph-reviewer subagent (subagent_type=ralph-reviewer); does NOT fall back to general-purpose
- [ ] #7 Chat output includes verdict line and drift list only; full matrix is in the saved file
<!-- AC:END -->
