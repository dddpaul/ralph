---
id: TASK-98
title: Switch ralph-sync allowlist rule and SKILL.md invocation to relative path
status: Done
assignee: []
created_date: '2026-05-03 14:29'
updated_date: '2026-05-03 14:32'
labels:
  - skill
  - ralph-sync
  - refactor
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-97 set the allowlist rule to an absolute host path (Bash(bash /Users/paul/Private/Projects/ai/ralph/.claude/skills/ralph-sync/sync.sh:*)). This is brittle: it breaks if the user moves the repo, and it assumes one specific host layout.

Switch both halves to a relative path:
1. SKILL.md: replace 'git rev-parse --show-toplevel'-based absolute invocation with a bare relative invocation 'bash .claude/skills/ralph-sync/sync.sh <mode>'. Add a one-line note that the skill is project-local and Claude Code's cwd is the repo root when it loads.
2. .claude/settings.local.json: change the allowlist rule from the absolute host path to 'Bash(bash .claude/skills/ralph-sync/sync.sh:*)' (gitignored — local edit only, document in task notes).

Trade-off accepted: if the user invokes /ralph-sync from a subdirectory (which is unusual for project-local skills), the relative path fails. This is acceptable because (a) project-local skills are loaded only when Claude Code's cwd is the project root, (b) the skill is intrinsically Ralph-repo-only, and (c) portability across machines/repo-moves is a more common need.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SKILL.md uses bare relative path 'bash .claude/skills/ralph-sync/sync.sh <mode>' for all three modes (classify, apply, diff); the 'git rev-parse --show-toplevel' resolution step is removed
- [x] #2 SKILL.md gains a one-line note about cwd assumption (project-local skill loads with cwd = repo root)
- [x] #3 Allowlist rule in .claude/settings.local.json (gitignored — verify directly via grep, not diff): contains 'Bash(bash .claude/skills/ralph-sync/sync.sh:*)' and does NOT contain the absolute-path version anymore
- [x] #4 task-reviewer (subagent_type=task-reviewer) returns APPROVED on git diff master..HEAD AND applies R13 strictly
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
AC #3 verification (gitignored file): grep .claude/settings.local.json shows the new relative rule at line 31. The previous absolute-path rule has been replaced. Local edit only — won't appear in git diff.

Commit: `537205f` - task-98: Switch ralph-sync to relative path

task-reviewer APPROVED at commit 537205f. R13 strictly applied — AC #3 verified directly against live gitignored file. All 4 ACs satisfied.
<!-- SECTION:NOTES:END -->
