---
id: TASK-125
title: Scope master-branch-guard to project tree; drop /tmp special case
status: In Progress
assignee: []
created_date: '2026-05-17 09:06'
updated_date: '2026-05-17 12:36'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem with current design

TASK-124 added a /tmp exemption to master-branch-guard.sh as a one-off. But /tmp is just a specific instance of a general truth: **the guard's purpose is to prevent uncommitted-on-master changes to the project tree, not to police paths anywhere on the filesystem.**

Today's hook denies any path that isn't explicitly allowlisted. That means every scratch-file location outside the project (\`/tmp\`, \`$TMPDIR\`, \`$HOME/Downloads\`, etc.) needs its own exemption case. That's the wrong direction — exemptions multiply.

## What

Replace the path-allowlist model with a project-scope model:

1. Resolve the project root via \`git rev-parse --show-toplevel\`.
2. If the tool's target path is **outside** the project root → exit 0 unconditionally (no block).
3. If the path is **inside** the project root → apply the existing exemptions (.claude/, design/, .gitignore basename) and otherwise emit the BLOCKED deny JSON.

This single change makes /tmp work naturally and also handles every other off-project path (Downloads, Desktop, $TMPDIR, sibling repos) without adding more case statements.

Drop the artifacts that TASK-124 added but are no longer needed:
- The \`/tmp/*|/private/tmp/*\` case in master-branch-guard.sh (live + template)
- \`Write(/tmp/**)\` and \`Edit(/tmp/**)\` in template settings.local.json (live copy is gitignored — user can clean up manually)

## Edge cases

- **Path resolution.** tool_input.file_path is normally absolute, but may be relative. Prefix relative paths with PWD before the prefix-check.
- **Symlinks.** macOS /tmp resolves to /private/tmp; the project root may also be under a symlinked parent. The check should not require canonicalization (which adds I/O dependency on \`realpath\`/\`readlink -f\`); a literal prefix match is good enough for the common case. Document this limitation as a known minor edge — if someone passes /tmp/... and the project is also under /tmp (rare), the path is correctly identified as in-project.
- **Not in a git repo.** If \`git rev-parse --show-toplevel\` fails or returns empty, exit 0 (don't block). Same fail-open philosophy as the existing branch check.

## Source files

- \`.claude/hooks/master-branch-guard.sh\` (live)
- \`skills/ralph-init/templates/claude/hooks/master-branch-guard.sh\` (template, R11 parity)
- \`skills/ralph-init/templates/claude/settings.local.json\` (remove the two /tmp entries)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .claude/hooks/master-branch-guard.sh resolves project root via 'git rev-parse --show-toplevel' and exits 0 when the target path is outside that root
- [x] #2 .claude/hooks/master-branch-guard.sh no longer contains a literal '/tmp/*|/private/tmp/*' case branch (the broader outside-project check supersedes it)
- [x] #3 skills/ralph-init/templates/claude/hooks/master-branch-guard.sh is byte-for-byte identical to the live .claude/hooks/master-branch-guard.sh (R11 parity)
- [x] #4 skills/ralph-init/templates/claude/settings.local.json permissions.allow no longer contains 'Write(/tmp/**)' or 'Edit(/tmp/**)'
- [x] #5 Behavior verified by branch-stripped hook test: /tmp/foo.txt exits 0 silently, $HOME/Downloads/foo.txt exits 0 silently, <project>/src/foo.txt emits BLOCKED, <project>/.claude/foo exits 0, <project>/design/foo exits 0, <project>/.gitignore exits 0
- [x] #6 Behavior verified for the not-in-git-repo case: hook exits 0 silently when 'git rev-parse --show-toplevel' fails
- [x] #7 bash -n on both .claude/hooks/master-branch-guard.sh copies passes
- [ ] #8 After merge, bash .claude/skills/ralph-sync/sync.sh classify shows skill ralph-init as [unchanged] (post-sync)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation: rewrote master-branch-guard.sh to compute project_root via git rev-parse --show-toplevel; paths outside the root exit 0 silently. Removed the literal /tmp/* case (subsumed). R11 parity verified (live + template byte-identical). Behavior tests (with branch guard stripped): /tmp/foo, /Users/paul/Downloads/foo, /private/tmp/foo, /Users/paul/Private/Projects/other/x all exit 0; in-tree src/foo emits BLOCKED; in-tree .claude/design/.gitignore exit 0. Not-in-git-repo case: exit 0. bash -n PASS on both copies. Removed Write/Edit /tmp entries from template settings.local.json.

Commit: `859ae4b` - task-125: Scope master-branch-guard to project tree

Reviewer APPROVED (859ae4b).
<!-- SECTION:NOTES:END -->
