---
id: TASK-318
title: Rewrite R-INFRA-6 to check merge provenance on master
status: In Progress
assignee: []
created_date: '2026-11-04T14:55:00Z'
updated_date: '2026-11-06T18:56:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-309
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Rewrite R-INFRA-6 in the shared infra rules bundle, so that it allows exactly the direct commits on master that the workflow and the protocol make, and checks where each merge came from.

What it allows:
- the master-branch guard's allowlist paths;
- task-N task-file commits;
- task-branch work whose merge parent, or fast-forwarded commits, match a recorded Review: APPROVED (sha) note;
- integration merges whose Integrated-Origin trailer is reachable from origin's base branch.

Merge-tree equality is an extra check against hand-resolved merges, not proof of approval.

The rule file is plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-024.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 R-INFRA-6 in `plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md` allows on master the master-branch guard allowlist paths and task-N commits that change only backlog task files
- [x] #2 The template CLAUDE.md Review step and this repo CLAUDE.md record the reviewed commit as Review: APPROVED (sha), the task branch tip the reviewer saw
- [x] #3 Task-branch work is allowed when a merge second parent equals a recorded APPROVED SHA with merge-tree equality, or fast-forwarded commits are at or behind such a SHA, with no surviving branch ref required
- [x] #4 An APPROVED verdict recorded for an earlier SHA does not approve later commits
- [x] #5 Integration merges are allowed when their Integrated-Origin trailer names the second parent, that SHA is reachable from origin base branch, and the tree equals git merge-tree of the parents
- [x] #6 A merge whose tree differs is allowed only with an Integration review: APPROVED note for exactly that merge SHA
- [x] #7 Fixtures approve a design/ commit, a task-file commit, a reviewed merge with its branch deleted, a reviewed fast-forward, a clean integration merge and a hand-resolved merge with an integration review
- [x] #8 Fixtures flag a clean merge from an unreviewed task branch, a clean merge from an arbitrary side branch, a stale-verdict merge and a hand-edited merge without an integration review
- [x] #9 ruff, pytest and bats pass
- [x] #10 After the CLAUDE.md Review step wording changes, .claude/managed-file-drift.accept's CLAUDE.md line is refreshed to the new template and project hashes (via managed-file-drift.sh accept), so the drift warning does not return
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: ship plugins/ralph/scripts/master-provenance.sh, a deterministic checker the reviewer runs for R-INFRA-6 over the unpushed master range (origin/master..master by default). It walks first-parent commits: allowlist-path commits and task-N task-file commits pass; task merges pass when P2 is reachable from a recorded 'Review: APPROVED <sha>' of the named task with only bookkeeping commits after it and the tree equals git merge-tree; fast-forwarded task commits pass at or behind such a SHA; integration merges pass on a matching Integrated-Origin trailer reachable from origin base and merge-tree equality; differing trees need 'Integration review: APPROVED <merge-sha>'. Rewrite R-INFRA-6 to require it, update the CLAUDE.md Review step (template + repo) to record the SHA, refresh the drift accept line, and add pytest fixtures.

Commit: `6021ec6` - task-318: check merge provenance on master for R-INFRA-6

Implementation: master-provenance.sh in plugins/ralph/scripts (bash 3.2/BSD-safe, needs git 2.38+ for merge-tree --write-tree). Bookkeeping commits (task-N task-file commits, guard allowlist paths, master_bookkeeping_paths) may follow the APPROVED SHA, because the lifecycle commits the note, Done status and version bump after the review. .claude/task-reviewer.conf (now tracked, also in ralph-init's .gitignore block) sets master_bookkeeping_paths to the two plugin manifests and master_provenance_since to the TASK-317 merge, since older merges carry no Review: APPROVED notes. Tests: tests/python/test_master_provenance.py (6 approved + 4 flagged AC fixtures, plus extra cases). pytest 1432 passed; bats 0 failures; ruff clean on new files (49 pre-existing errors, identical on master).

Review round 1 (CHANGES REQUESTED) fixes: fast-forward approval now needs the APPROVED SHA on master's first-parent line, so a code commit made on master before a --no-ff-merged branch forked is flagged (the pure fast-forward variant is undetectable from a tip SHA; documented in R-INFRA-6); without origin/master the checker walks all of master; --remote/--base without a value exit 2; R-INFRA-6 states the bookkeeping-after-SHA condition directly.
<!-- SECTION:NOTES:END -->
