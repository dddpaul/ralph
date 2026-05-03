---
id: TASK-92
title: >-
  Move task-reviewer agent to top-level agents/ folder; ralph-init verifies
  user-global as prereq
status: Done
assignee: []
created_date: '2026-05-03 06:55'
updated_date: '2026-05-03 07:16'
labels:
  - agent
  - ralph-init
  - refactor
  - distribution
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Promote agents to first-class distributable user-global content, parallel to skills/. Single canonical location eliminates the live/template/user-global drift hit in TASK-88 and TASK-91.

## Repo restructure
- 'git mv .claude/agents/task-reviewer.md agents/task-reviewer.md' — new top-level distributable folder, parallel to skills/.
- 'git rm -r .claude/agents/' — directory deleted; project-local agents are no longer a supported pattern (only project-local *rules* are).
- 'git rm skills/ralph-init/templates/claude/agents/task-reviewer.md' and remove the now-empty templates/claude/agents/ directory.

## ralph-init SKILL.md changes
- **Step 1 (Preflight)**: add hard-fail prereq check: '[ -s "$HOME/.claude/agents/task-reviewer.md" ]' or print 'ERROR: ~/.claude/agents/task-reviewer.md missing. Copy it from the Ralph repo: cp <ralph-repo>/agents/task-reviewer.md ~/.claude/agents/' and exit 1. Aborts BEFORE any project files are written.
- **Step 3.4 (.gitignore append block)**: drop '\!.claude/agents/' since the directory no longer exists. Final block: '.claude/*' / '\!.claude/settings.json' / '\!.claude/task-reviewer-rules.md' / '\!.claude/hooks/'.
- **Step 3.7**: drop the 'Read templates/claude/agents/task-reviewer.md → write to .claude/agents/task-reviewer.md' line. Update section title (no more 'agents/').
- **Step 4 (Summary)**: drop the '.claude/agents/task-reviewer.md - Code review agent' line.
- **U2 (Upgrade detection)**: drop the agent rows (project-local agents no longer exist).
- **U4 (Apply updates)**: drop the agent overwrite step.
- ralph-init's upgrade flow does NOT manage ~/.claude/agents/* (symmetric with skills — user re-copies from the Ralph repo when they pull updates).

## Project .gitignore
- Drop '\!.claude/agents/' since the directory no longer exists. Final block matches the SKILL.md block above.

## task-reviewer-rules.md updates
- **R3** (frontmatter requirement): broaden path scope to 'agents/*.md' (top-level), '.claude/agents/*.md' (project-local, kept as a category even if Ralph itself ships none), and '~/.claude/agents/*.md' (user-global). Remove the 'or its template mirror under skills/ralph-init/templates/claude/agents/' clause.
- **R4** (frontmatter doesn't take effect mid-session): same path broadening.
- **R11** (template parity): remove the agent parity row from the table. Add a second carve-out paragraph after the existing task-reviewer-rules.md exclusion: 'Excluded from parity (user-global distribution): files under agents/ are user-global content distributed manually; the user copies them to ~/.claude/agents/, the same way they copy skills/* to ~/.claude/skills/. ralph-init does NOT mirror these into project-local .claude/agents/ and there is NO template under skills/ralph-init/templates/claude/agents/. Do NOT flag the absence of a template mirror for agent files.'

## README.md
- Add or expand a 'First-time setup' section with both copies and hard-fail prereq messaging:
  - 'cp -r agents/* ~/.claude/agents/'
  - 'cp -r skills/* ~/.claude/skills/'
- Mention that ralph-init aborts if either prereq is missing.
- Add an 'Updating' note: when the user 'git pull's new versions of agents/ or skills/, they must re-run the copy. ralph-init does not manage ~/.claude/.

## Out of scope (do not include)
- Bootstrap script that automates the copy (separate follow-up task if the manual cp becomes annoying).
- Migrating other potential agents — this task ships only task-reviewer; future agents follow the same pattern.
- Touching ~/.claude/agents/task-reviewer.md (user-global state is owned by the user, not by ralph-init or this task).

## Design rationale
Brainstorm output (this session): single canonical agent file eliminates drift (the user's primary motive). Top-level agents/ folder gives agents the same first-class status as skills/, keeping the distribution model symmetric and the bootstrap step uniform.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 git mv .claude/agents/task-reviewer.md to agents/task-reviewer.md; .claude/agents/ directory deleted; skills/ralph-init/templates/claude/agents/task-reviewer.md deleted; templates/claude/agents/ empty parent removed if empty
- [x] #2 ralph-init SKILL.md Step 1 (Preflight) gains a hard-fail prereq that aborts if ~/.claude/agents/task-reviewer.md is missing, with a copy instruction in the error message
- [x] #3 ralph-init SKILL.md Step 3.4 gitignore-append block, Step 3.7 (no agent install line), Step 4 summary, U2 detection list, and U4 apply list all updated to remove agent references
- [x] #4 Project .gitignore drops '\!.claude/agents/' (directory no longer exists)
- [x] #5 .claude/task-reviewer-rules.md R3 and R4 paths broadened to cover agents/, .claude/agents/, and ~/.claude/agents/; template-mirror clause removed
- [x] #6 .claude/task-reviewer-rules.md R11 table loses the agent row; second carve-out paragraph added explaining user-global distribution
- [x] #7 README.md gains a 'First-time setup' section listing both 'cp -r agents/* ~/.claude/agents/' and 'cp -r skills/* ~/.claude/skills/' as prereqs, plus an 'Updating' note that ralph-init does not manage ~/.claude/
- [x] #8 task-reviewer agent (subagent_type=task-reviewer) returns APPROVED on git diff master..HEAD AND reports 'Custom rules applied from project tier: .claude/task-reviewer-rules.md' (smoke test that the new top-level agent location is loaded by user-global ~/.claude/agents/task-reviewer.md without project-local fallback)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Restore .claude/task-reviewer-rules.md from HEAD. (2) git mv .claude/agents/task-reviewer.md agents/task-reviewer.md. (3) git rm templates/claude/agents/task-reviewer.md + remove empty dirs. (4) Update ralph-init SKILL.md: preflight, 3.4, 3.7, Step 4, U2, U4. (5) Update .gitignore. (6) Update task-reviewer-rules.md R3, R4, R11. (7) Update README.md. (8) Run task-reviewer.

Commit: `3dc64fd` - task-92: Promote task-reviewer agent to top-level agents/ folder

task-reviewer APPROVED (commit 3dc64fd). Reviewer noted: (1) user-global rules fallback path is ~/.claude/agents/task-reviewer-rules.md — this was the pre-existing path, not a new change. (2) YAML frontmatter absent from agents/task-reviewer.md — intentional per design, frontmatter is added by user when copying to ~/.claude/agents/.
<!-- SECTION:NOTES:END -->
