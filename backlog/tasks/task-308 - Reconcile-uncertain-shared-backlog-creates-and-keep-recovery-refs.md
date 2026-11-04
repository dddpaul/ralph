---
id: TASK-308
title: Reconcile uncertain shared-backlog creates and keep recovery refs
status: To Do
assignee: []
created_date: '2026-11-04T14:53:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-307
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make create safe on lost races and uncertain pushes.

Retries:
- After a lost race, it reallocates with the same operation ID.
- After an uncertain push, it reconciles against origin by operation ID, and never allocates again without that check.

Recovery:
- A refs/ralph/recovery ref keeps an uncertain commit.
- Every temporary worktree is removed on every exit.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-014.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After a non-fast-forward rejection, create reallocates in a fresh worktree with the same operation ID, at most 3 times
- [ ] #2 After an uncertain push, create fetches and looks for its operation ID on origin and, if found, reports that ID, path and SHA as the result
- [ ] #3 If reconciliation fails, create stops without allocating again
- [ ] #4 Before removing a worktree whose commit acceptance is uncertain, create stores the commit under refs/ralph/recovery/(op-id) and prints how to finish or drop it
- [ ] #5 Every temporary worktree is removed on every exit (success, failure, deadline, signal) after any recovery ref is saved
- [ ] #6 Tests show an ambiguous push that origin accepted is not repeated, a failed reconciliation stops, and the recovery ref survives worktree removal
- [ ] #7 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->
