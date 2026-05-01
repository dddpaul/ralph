---
id: TASK-81
title: >-
  Add custom-rules loading to task-reviewer agent (two-tier,
  project-takes-precedence)
status: To Do
assignee: []
created_date: '2026-05-01 16:09'
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
- [ ] #1 Update .claude/agents/task-reviewer.md and skills/ralph-init/templates/task-reviewer.md with a 'Custom Rules Loading' section at the top of the agent prompt that runs the resolver and applies the output as additional review criteria
- [ ] #2 Project tier (.claude/agents/task-reviewer-rules.md) takes precedence over user-global tier (~/.claude/agents/task-reviewer-rules.md)
- [ ] #3 Empty file at either tier is treated as absent and falls through to the next tier
- [ ] #4 Agent reports at the top of its review which custom rules applied and from which tier
- [ ] #5 Standard review checklist still runs even when no rules file exists at either tier
- [ ] #6 Manual smoke test: write a project-level rules file with one rule, run the reviewer on a fake diff, confirm the rule is mentioned in the review
- [ ] #7 Manual smoke test: with no project-level file, write a user-global rules file with one rule, run the reviewer, confirm the user-global rule is mentioned
- [ ] #8 Manual smoke test: with both tiers populated, confirm only project-level rules are applied
<!-- AC:END -->
