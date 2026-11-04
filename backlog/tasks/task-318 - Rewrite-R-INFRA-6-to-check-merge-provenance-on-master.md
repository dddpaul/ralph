---
id: TASK-318
title: Rewrite R-INFRA-6 to check merge provenance on master
status: To Do
assignee: []
created_date: '2026-11-04T14:55:00Z'
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
- [ ] #1 R-INFRA-6 in `plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md` allows on master the master-branch guard allowlist paths and task-N commits that change only backlog task files
- [ ] #2 The template CLAUDE.md Review step and this repo CLAUDE.md record the reviewed commit as Review: APPROVED (sha), the task branch tip the reviewer saw
- [ ] #3 Task-branch work is allowed when a merge second parent equals a recorded APPROVED SHA with merge-tree equality, or fast-forwarded commits are at or behind such a SHA, with no surviving branch ref required
- [ ] #4 An APPROVED verdict recorded for an earlier SHA does not approve later commits
- [ ] #5 Integration merges are allowed when their Integrated-Origin trailer names the second parent, that SHA is reachable from origin base branch, and the tree equals git merge-tree of the parents
- [ ] #6 A merge whose tree differs is allowed only with an Integration review: APPROVED note for exactly that merge SHA
- [ ] #7 Fixtures approve a design/ commit, a task-file commit, a reviewed merge with its branch deleted, a reviewed fast-forward, a clean integration merge and a hand-resolved merge with an integration review
- [ ] #8 Fixtures flag a clean merge from an unreviewed task branch, a clean merge from an arbitrary side branch, a stale-verdict merge and a hand-edited merge without an integration review
- [ ] #9 ruff, pytest and bats pass
<!-- AC:END -->
