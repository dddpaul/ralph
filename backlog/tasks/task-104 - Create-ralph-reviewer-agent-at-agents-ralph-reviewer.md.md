---
id: TASK-104
title: Create ralph-reviewer agent at agents/ralph-reviewer.md
status: Done
assignee: []
created_date: '2026-05-08 19:05'
updated_date: '2026-05-08 19:23'
labels:
  - 'feature:ralph-review'
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a new top-level agent at agents/ralph-reviewer.md (mirrors agents/task-reviewer.md location). Distributed via ralph-sync to ~/.claude/agents/.

The agent performs cumulative cross-task feature review:
- Reads design/<name>-prd.md (optional) and design/<name>-brainstorm.md (optional) — at least one must exist
- Reads in-scope backlog task files (titles, descriptions, ACs, notes)
- Reads cumulative git diff <base>..HEAD
- Applies a 5-pass rubric:
  1. PRD coverage — each US-N/FR-N delivered/partial/missing (skipped if no PRD)
  2. Non-goal protection — accidental shipping of PRD non-goals
  3. Brainstorm scope cuts — verifies cuts still respected (skipped if no brainstorm)
  4. Success-metric realism — measurable post-merge or hypothesis (skipped if no Success Metrics section)
  5. Out-of-scope creep — diff hunks not traceable to PRD/brainstorm
- Produces verdict: Aligned / Partial / Drifted, plus matrix and drift list
- Loads project-tier custom rules from .claude/ralph-review-rules.md if present (parallel to task-reviewer's pattern)

Frontmatter required (per R3): name: ralph-reviewer, description: <one-line>, color: <pick one>.

Agent file structure mirrors task-reviewer.md: frontmatter, role description, rubric, output format, custom-rules loading note.

Out of scope: the /ralph-review skill that invokes this agent (TASK-105), README updates, migration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 agents/ralph-reviewer.md exists with valid YAML frontmatter (name: ralph-reviewer, description, color)
- [x] #2 Agent prompt body covers all 5 rubric passes (PRD coverage, non-goal protection, brainstorm scope cuts, success-metric realism, out-of-scope creep) with skip conditions when input is missing
- [x] #3 Agent verdict scale is exactly: Aligned / Partial / Drifted (not numeric, not other words)
- [x] #4 Agent loads project-tier custom rules from .claude/ralph-review-rules.md if present, mirroring task-reviewer.md's loader
- [x] #5 Agent body explicitly notes verdict only weighs passes that ran (per Section 4 revision)
- [x] #6 Output format specifies a Markdown deliverable with Verdict, Intent→Implementation matrix, Drift list, Reviewer notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Create agents/ralph-reviewer.md mirroring task-reviewer.md structure. Frontmatter with name/description/color, custom rules loader for .claude/ralph-review-rules.md, 5-pass rubric with skip conditions, verdict scale (Aligned/Partial/Drifted), markdown output format.

Commit: `3dccaa7` - task-104: Add ralph-reviewer agent for cumulative feature review

Implemented: agents/ralph-reviewer.md with 5-pass rubric, Aligned/Partial/Drifted verdict, custom rules loader, markdown output format. Reviewed and approved.
<!-- SECTION:NOTES:END -->
