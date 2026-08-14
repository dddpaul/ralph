---
id: TASK-223
title: >-
  Add explicit design sign-off gate before Phase 4 task creation in
  brainstorm-rules template
status: Done
assignee: []
created_date: '2026-08-09 11:24'
updated_date: '2026-08-14 09:44'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Brainstorm Phase 4 currently makes "Create backlog task(s)" the mandatory first option, and nothing in the rules distinguishes *selecting that option* from the user *approving the design*. In practice this leads to tasks being created prematurely — before the human has actually read and signed off on the design. Add an explicit design sign-off gate so `ralph-task` / `backlog task create` cannot run on inference; a separate, explicit user approval is required first. This was prototyped and validated as a project-level override in a downstream project (the offdesk-review-first variant) — this task upstreams only the generalizable half.

## Scope

In scope:
- Add an explicit design sign-off gate to the canonical brainstorm-rules template distributed by ralph-init: task creation (`ralph-task` / `backlog task create`) MUST NOT be invoked until the user explicitly approves the design in-session (e.g. "design ok", "create the task"). Selecting a Phase 4 option is NOT itself sign-off.
- Make the rule state that on any ambiguity the assistant stops and asks — never creates the task on inference.
- Keep the ralph repo's own dogfood copy (.claude/brainstorm-rules.md) in sync with the template change.
- Document (as a note/example only) that a review-first step — e.g. pushing the design to an off-desk vault — belongs in the "Project additions" upgrade-safe zone, not the canonical template.

Out of scope:
- Hardcoding any offdesk / off-desk-review step into the canonical template. Offdesk is a downstream user-level skill not every ralph project has; it stays a project addition, not a template default.
- Changing the "Distilled for ralph-task" producer/consumer contract or the feature-label hand-off (TASK-118) behavior.
- Editing the umputun brainstorm skill's own files (the skill loads brainstorm-rules.md; do not modify the skill package).
- Section-based merge machinery for ralph upgrade (already handled by TASK-119).

## Files

- `plugins/ralph/skills/ralph-init/templates/claude/brainstorm-rules.md` (exists) — canonical template ralph-init installs into each project's .claude/; add the sign-off gate to the "Phase 4 Override" and/or "In both cases" section.
- `.claude/brainstorm-rules.md` (exists) — ralph's own dogfood copy; mirror the same change so the repo stays self-consistent.
- `plugins/ralph/skills/ralph-task/SKILL.md` (exists) — consumer side; confirm (and, if needed, note) that the create flow honors the sign-off gate before `backlog task create`.

## Source

Source: /Users/paul/Private/Alfa/Projects/equation/services@3db57edc24e2-dirty
Reference (read-only, do NOT copy verbatim): in the source repo, .claude/brainstorm-rules.md "Project additions" > "Phase 4 gate: offdesk review + explicit design sign-off before task creation" is the downstream prototype. Upstream only the explicit-sign-off half; leave the offdesk-first half as a project-specific example.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC (especially: do NOT hardcode offdesk into the template).

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Canonical template plugins/ralph/skills/ralph-init/templates/claude/brainstorm-rules.md states that ralph-task / backlog task create MUST NOT be invoked until the user explicitly approves the design in-session
- [x] #2 The template makes explicit that selecting a Phase 4 option is NOT itself sign-off; a separate explicit approval is required
- [x] #3 The template instructs the assistant to stop and ask on any ambiguity, never creating the task on inference
- [x] #4 The ralph dogfood copy .claude/brainstorm-rules.md carries the same sign-off-gate wording as the template
- [x] #5 No mandatory offdesk/off-desk-review step is hardcoded in the canonical template; grep of the template shows offdesk referenced only as a Project-additions example, or not at all
- [x] #6 The existing Phase 4 'first option = Create backlog task(s)' language and the 'Distilled for ralph-task' contract remain intact (change is additive, not a rewrite)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Insert an additive '### Design sign-off gate' subsection into the Phase 4 Override section of the canonical template plugins/ralph/skills/ralph-init/templates/claude/brainstorm-rules.md: ralph-task/backlog task create MUST NOT run until explicit in-session user approval (AC1); selecting a Phase 4 option is NOT sign-off, separate approval required (AC2); on any ambiguity stop and ask, never create on inference (AC3); include a blockquote framing offdesk/off-desk review as a Project-additions example only, not a template default (AC5, scope note). (2) Mirror byte-identically to dogfood .claude/brainstorm-rules.md (AC4, R11 parity). (3) Additive only — leave 'first option = Create backlog task(s)' and 'Distilled for ralph-task' contract intact (AC6). (4) Add a minimal consumer-boundary note to ralph-task/SKILL.md Pre-checks reinforcing the gate. (5) Lint (ruff), verify no .py changed; grep-verify each AC; task-reviewer; bump-version.sh --auto (shipped plugin files changed).

Commit: `a6da0c2` - task-223: add design sign-off gate before Phase 4 task creation in brainstorm-rules template + dogfood copy; consumer note in ralph-task

Done: Added additive '### Design sign-off gate — before any task creation' subsection to the Phase 4 Override section of the canonical template (plugins/ralph/skills/ralph-init/templates/claude/brainstorm-rules.md): ralph-task/backlog task create MUST NOT run until explicit in-session user approval (AC1); selecting a Phase 4 option is NOT sign-off, separate approval required (AC2); on any ambiguity stop and ask, never create on inference (AC3). Mirrored byte-identically to the dogfood .claude/brainstorm-rules.md (AC4, R11 parity verified via diff). offdesk/off-desk review appears once, framed only as a Project-additions example, never hardcoded (AC5). Existing 'first option = Create backlog task(s)' and the 'Distilled for ralph-task' contract left intact — change is purely additive (AC6). Added a minimal consumer-boundary note to ralph-task/SKILL.md Pre-checks reinforcing that feature=<slug> invocation is not proof of sign-off. Gate: uv run ruff check . clean; uv run pytest 346 passed; no .py changed. Review: task-reviewer agent returned APPROVED (R11 parity byte-identical, no-hard-wrap convention respected).

Commit: `ffc63b7` - task-223: bump plugin version to 0.3.3 (patch)
<!-- SECTION:NOTES:END -->
