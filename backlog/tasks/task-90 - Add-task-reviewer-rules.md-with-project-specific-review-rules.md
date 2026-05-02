---
id: TASK-90
title: Add task-reviewer-rules.md with project-specific review rules
status: Done
assignee: []
created_date: '2026-05-02 17:38'
updated_date: '2026-05-02 17:47'
labels:
  - agent
  - task-reviewer
  - custom-rules
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Write the project-level custom rules file '.claude/agents/task-reviewer-rules.md' that the task-reviewer agent loads as additional review criteria (mechanism added in TASK-81 but rules file was never written).

Twelve strict rules distilled from recurring mistakes across the Ralph project:

R1  Review the diff (git diff master..HEAD), not the working tree
R2  Every AC must be checked or explicitly deferred with a reason
R3  Agent files require valid YAML frontmatter (name, description)
R4  Frontmatter changes do not take effect mid-session
R5  Shell scripts must work on both GNU and BSD tools
R6  No over-broad shell permission rules in settings.local.json
R7  No AI-attribution trailers in commits
R8  Hook commands reference scripts, not inline bash blobs
R9  Use git ls-files / git log as truth, not ls / find
R10 Don't bypass master-branch-guard.sh via dangerouslyDisableSandbox
R11 Template parity: .claude/* mirrors skills/ralph-init/templates/claude/*; ralph.sh mirrors templates/root/ralph.sh
R12 Markdown deliverables must be logically consistent and non-contradictory; every AC traceable to a section

Tone: strict, prohibitive (MUST / MUST NOT). Project-level only. Mirror to skills/ralph-init/templates/claude/agents/task-reviewer-rules.md per R11 (template parity).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Project rules file '.claude/agents/task-reviewer-rules.md' exists with all 12 rules in strict prohibitive tone
- [x] #2 Template mirror 'skills/ralph-init/templates/claude/agents/task-reviewer-rules.md' has identical content (template parity per R11)
- [x] #3 Each rule has a one-line title and a body explaining what to flag and why
- [x] #4 task-reviewer agent (subagent_type=task-reviewer) returns APPROVED on git diff master..HEAD AND reports 'Custom rules applied from project tier' at the top of the review (self-bootstrap test of TASK-81 loading mechanism)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Draft .claude/agents/task-reviewer-rules.md with 12 rules in strict prohibitive tone.
2. Mirror identical content to skills/ralph-init/templates/claude/agents/task-reviewer-rules.md (template parity per R11).
3. Spawn task-reviewer (subagent_type=task-reviewer) on git diff master..HEAD — this is also the smoke test for TASK-81's loading mechanism (project tier rules now exist for the first time, agent must report 'Custom rules applied from project tier').
4. Mark Done; merge to master.

Commit: `dca06a6` - task-90: Add task-reviewer-rules.md with 12 project review rules

task-reviewer (subagent_type=task-reviewer) APPROVED on commit dca06a6. Custom rules loading from project tier verified live in the review (smoke test for TASK-81 mechanism passed — agent reported all 12 loaded rule titles). Template parity byte-perfect (R11). All 4 ACs satisfied.

Note: encountered .gitignore bug — new files in .claude/agents/ are matched by the .claude/ exclusion despite negation patterns (line 17 of .gitignore). Existing tracked files unaffected. Used git add -f to bypass for this commit; follow-up TASK-91 will fix the gitignore properly.
<!-- SECTION:NOTES:END -->
