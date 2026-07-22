---
id: TASK-208
title: ralph-refine SKILL.md and single-approval launch flow
status: To Do
assignee: []
created_date: '2026-07-22 16:29'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-206
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-008 of ralph-refine. Add the ralph-refine SKILL.md so the skill is separately invocable and documents the single-approval launch flow (one sandbox-bypass prompt, mirroring ralph-run). See design/ralph-refine-prd.md US-008 and doc-4 invariant 4.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 plugins/ralph/skills/ralph-refine/SKILL.md exists with a description that makes the skill separately invocable/discoverable
- [ ] #2 Documents invocation: ./refine.sh --prompt/--author/--reviewer, the --draft mode, --type, --threshold, and output landing in iterations/
- [ ] #3 References the bundled example role sets
- [ ] #4 No plugin.json edit required (skills auto-discover) — verified the skill is listed by the plugin loader
- [ ] #5 Single-approval flow: when the skill launches refine on the user's behalf, exactly one permission prompt fires (the sandbox-bypass refine.sh launch); the SKILL.md documents this and issues the launch as a single sandbox-bypass Bash call
- [ ] #6 Any helper command the SKILL.md runs is either a read-only sandbox-safe check or a bash <abs-path> shim covered by a seeded Bash(bash <abs-path>:*) allow rule — no second prompt
<!-- AC:END -->
