---
id: TASK-105
title: Create /ralph-review skill at skills/ralph-review/SKILL.md
status: Done
assignee: []
created_date: '2026-05-08 19:05'
updated_date: '2026-05-08 19:29'
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
- [x] #1 skills/ralph-review/SKILL.md exists with valid YAML frontmatter and clear trigger keywords (ralph review, cumulative review, review feature)
- [x] #2 Pre-conditions enforced: BLOCKED messages match the exact strings designed in Section 4
- [x] #3 Tasks resolution supports both 'feature:<name>' label and explicit tasks= override (Approach D)
- [x] #4 Diff base derivation reads 'Commit:' hashes from in-scope task files (not git log inference)
- [x] #5 Output saved to design/<name>-review-<YYYY-MM-DD>.md with -NN suffix on collision (never overwrites)
- [x] #6 Spawns ralph-reviewer subagent (subagent_type=ralph-reviewer); does NOT fall back to general-purpose
- [x] #7 Chat output includes verdict line and drift list only; full matrix is in the saved file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Create skills/ralph-review/SKILL.md with YAML frontmatter and trigger keywords. Implement 6 steps: (1) parse args name= and optional tasks=, (2) pre-condition checks for design docs and done tasks, (3) diff base derivation from Commit: hashes in task files, (4) bundle building (brainstorm + PRD + task summaries + diff), (5) spawn ralph-reviewer agent, (6) save output and report. Follow existing skill patterns from ralph-run/ralph-prd for structure.

Commit: `2d6eb64` - task-105: Add ralph-review skill for cumulative feature review

Commit: `f74af10` - task-105: Fix Commit: hash regex and earliest-commit derivation

Implemented skills/ralph-review/SKILL.md with 6-step orchestration: arg parsing, pre-conditions (design docs + done tasks + diff range), bundle building, ralph-reviewer agent spawn, output persistence with collision handling, and chat reporting. Fixed Commit: hash regex to match backtick-wrapped format and improved earliest-commit derivation to sort by commit date.
<!-- SECTION:NOTES:END -->
