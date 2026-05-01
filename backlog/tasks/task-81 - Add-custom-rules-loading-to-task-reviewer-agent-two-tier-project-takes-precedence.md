---
id: TASK-81
title: >-
  Add custom-rules loading to task-reviewer agent (two-tier,
  project-takes-precedence)
status: Done
assignee: []
created_date: '2026-05-01 16:09'
updated_date: '2026-05-01 19:10'
labels:
  - agent
  - task-reviewer
  - custom-rules
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the task-reviewer agent so it loads optional custom review rules from a markdown file before reviewing the diff. Inspired by the brainstorm skill's rules mechanism, but agent-scoped.

Rationale: when a task produces specialised output (e.g. a .pptx deck), the reviewer should also apply project- or user-specific style guides (e.g. pptx-arch-style, pptx-core-style) without bloating the agent prompt. A free-form rules file lets the user point the reviewer at relevant style skills per pattern.

Tier layout (project takes precedence):
- Project: .claude/agents/task-reviewer-rules.md
- User-global: ~/.claude/agents/task-reviewer-rules.md
- Empty file at either tier is treated as absent (falls through).

Resolver (inline bash in the agent prompt):
  if [ -s .claude/agents/task-reviewer-rules.md ]; then cat .claude/agents/task-reviewer-rules.md
  elif [ -s "$HOME/.claude/agents/task-reviewer-rules.md" ]; then cat "$HOME/.claude/agents/task-reviewer-rules.md"
  fi

Agent behaviour: treat the resolver output as ADDITIONAL review criteria (supplements, does not replace, the standard checklist). At the top of the review, the agent must list which custom rules it applied and from which tier (project vs user-global).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Update .claude/agents/task-reviewer.md and skills/ralph-init/templates/task-reviewer.md with a 'Custom Rules Loading' section at the top of the agent prompt that runs the resolver and applies the output as additional review criteria
- [x] #2 Project tier (.claude/agents/task-reviewer-rules.md) takes precedence over user-global tier (~/.claude/agents/task-reviewer-rules.md)
- [x] #3 Empty file at either tier is treated as absent and falls through to the next tier
- [x] #4 Agent reports at the top of its review which custom rules applied and from which tier
- [x] #5 Standard review checklist still runs even when no rules file exists at either tier
- [ ] #6 Manual smoke test: write a project-level rules file with one rule, run the reviewer on a fake diff, confirm the rule is mentioned in the review
- [ ] #7 Manual smoke test: with no project-level file, write a user-global rules file with one rule, run the reviewer, confirm the user-global rule is mentioned
- [ ] #8 Manual smoke test: with both tiers populated, confirm only project-level rules are applied
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add 'Custom Rules Loading' section to top of both task-reviewer.md files. Section contains bash resolver that checks project tier first (.claude/agents/task-reviewer-rules.md), then user-global (~/.claude/agents/task-reviewer-rules.md). Empty files fall through. Agent reports which tier was used. Standard checklist is preserved.

Commit: `2c9d46b` - task-81: Add custom-rules loading to task-reviewer agent

Implementation complete. Both .claude/agents/task-reviewer.md and skills/ralph-init/templates/task-reviewer.md updated with Custom Rules Loading section. Two-tier resolver (project > user-global), empty files fall through via -s test. Code review approved.
<!-- SECTION:NOTES:END -->
