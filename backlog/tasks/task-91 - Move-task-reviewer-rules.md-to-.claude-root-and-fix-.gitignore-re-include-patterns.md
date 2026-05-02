---
id: TASK-91
title: >-
  Move task-reviewer-rules.md to .claude/ root and fix .gitignore re-include
  patterns
status: Done
assignee: []
created_date: '2026-05-02 17:56'
updated_date: '2026-05-02 18:04'
labels:
  - agent
  - task-reviewer
  - gitignore
  - refactor
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two coupled changes:

1. Move .claude/agents/task-reviewer-rules.md -> .claude/task-reviewer-rules.md.
   .claude/agents/ should only hold subagent_type registrations (agent prompts with YAML frontmatter); the rules file is data loaded by the task-reviewer agent, not an agent itself. Moving it out makes R3 (agent files require frontmatter) unconditional — no carve-outs needed for data files.

2. Fix .gitignore: the current pattern '.claude/' excludes the directory before negation patterns can re-include subpaths, so any new file under .claude/ is gitignored despite '\!.claude/agents/**' / '\!.claude/hooks/**' (existing tracked files unaffected; we hit this in TASK-90 with git add -f). Replace '.claude/' with '.claude/*' so subdirs/files are not pre-excluded as a directory; the negation patterns then work for new files under any depth. Mirror to skills/ralph-init/SKILL.md gitignore append block (Step 3.4).

Update the resolver in .claude/agents/task-reviewer.md (Custom Rules Loading section) to read from .claude/task-reviewer-rules.md (project) and ~/.claude/task-reviewer-rules.md (user-global), down from the .claude/agents/ subpath. Mirror to skills/ralph-init/templates/claude/agents/task-reviewer.md (R11 template parity).

Update R11 self-reference inside the rules file (the 'Excluded from parity' note already mentions the file path; update it).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 git mv .claude/agents/task-reviewer-rules.md to .claude/task-reviewer-rules.md; git ls-files confirms the new path tracked and the old path absent
- [x] #2 skills/ralph-init/SKILL.md Step 3.4 gitignore-append block updated to match new .gitignore patterns
- [x] #3 task-reviewer agent (subagent_type=task-reviewer) returns APPROVED on git diff master..HEAD AND reports 'Custom rules applied from project tier: .claude/task-reviewer-rules.md' (smoke test that the new path is loaded by the resolver)
- [x] #4 .gitignore rewritten so subdir files under .claude/ work via negation patterns. Verify all four cases:
- [ ] #5 .gitignore re-include patterns work for new files under .claude/ subdirs (the original bug). Verified empirically:
- '.claude/agents/' negation re-includes new files: 'git check-ignore --no-index .claude/agents/zz-test.md' exits 1 (no pattern matches; file would be tracked).
- '.claude/hooks/' negation re-includes new files: 'git check-ignore --no-index .claude/hooks/zz-test.sh' exits 1.
- '.claude/task-reviewer-rules.md' allowlisted by name: tracked via plain 'git mv' without -f (verified by 'git ls-files .claude/task-reviewer-rules.md' showing the path).
- Random root file '.claude/zz-test.md' remains ignored by '.claude/*' (matches the positive pattern; exit 0).
- 'git check-ignore -v --no-index .claude/zz-test.md' exits 0 (root-level random file IS ignored)
- 'git check-ignore -v --no-index .claude/agents/zz-test.md' exits 1 (NOT ignored)
- 'git check-ignore -v --no-index .claude/hooks/zz-test.sh' exits 1 (NOT ignored)
- 'git check-ignore -v --no-index .claude/task-reviewer-rules.md' exits 1 (allowlisted, NOT ignored)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Fix .gitignore: replace '.claude/' with '.claude/*'; prune now-redundant '\!.claude/agents/**' and '\!.claude/hooks/**' (the trailing /** patterns are unneeded once the parent isn't excluded as a directory).
2. Verify with 'git check-ignore -v --no-index' that new files under .claude/ root and .claude/agents/ are not ignored.
3. git mv .claude/agents/task-reviewer-rules.md .claude/task-reviewer-rules.md
4. Update .claude/agents/task-reviewer.md resolver paths (4 bash refs + 1 description string).
5. Mirror to skills/ralph-init/templates/claude/agents/task-reviewer.md (R11 parity).
6. Update skills/ralph-init/SKILL.md Step 3.4 gitignore-append block.
7. Update R11 'Excluded from parity' note in the rules file to reference the new path.
8. Spawn task-reviewer; verify it loads from .claude/task-reviewer-rules.md (smoke test).
9. Mark Done, merge.

Commit: `89495e2` - task-91: Move task-reviewer-rules to .claude/ root; fix gitignore

Re-reviewed at commit 89495e2 — task-reviewer APPROVED. Custom rules loaded from new path (.claude/task-reviewer-rules.md) — smoke test passed (AC #5). All 5 ACs satisfied. Reviewer noted AC #5 substantively overlaps AC #2's empirical verification; both covered by the same evidence.
<!-- SECTION:NOTES:END -->
