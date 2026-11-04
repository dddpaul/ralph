---
id: TASK-309
title: Make shared-backlog integrate merge-only and stop instead of renumbering
status: To Do
assignee: []
created_date: '2026-11-04T14:53:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-304
  - TASK-305
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make integrate merge origin and publish safely.

Merge and policy:
- It merges, never rebases, and writes an Integrated-Origin trailer.
- Its policy is fixed at invocation from the HEAD before the merge.
- It fails before merging when checks or their context are missing.

Duplicates: it stops with an old-to-new mapping and never renumbers.

Interruptions: it preserves an interrupted merge.

Retries: it retries only on a non-fast-forward rejection.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-015 and FR-9.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 integrate merges origin/master, never rebases, and its merge commit carries an Integrated-Origin trailer naming the fetched origin SHA
- [ ] #2 integrate takes its opt-in and checks policy from the pre-merge HEAD, fixed at invocation; tests cover merged-in commits that change checks and that remove the marker
- [ ] #3 integrate fails before merging when no checks are configured or their execution context is missing
- [ ] #4 On duplicate IDs integrate stops with an old-to-new mapping and neither pushes nor renumbers
- [ ] #5 An interrupted merge is preserved rather than reset, and a retry first checks for a clean state
- [ ] #6 integrate retries a push only on a non-fast-forward rejection, at most 3 times, and reports auth, hook and unreachable failures without retrying
- [ ] #7 bash -n, the bash 3.2 static guard and the shell tests pass; (host) the shell suite passes under /bin/bash 3.2
<!-- AC:END -->
