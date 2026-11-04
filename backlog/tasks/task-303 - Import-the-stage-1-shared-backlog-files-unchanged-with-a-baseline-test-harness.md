---
id: TASK-303
title: Import the stage-1 shared-backlog files unchanged with a baseline test harness
status: To Do
assignee: []
created_date: '2026-11-04T14:53:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Import a sibling project's proven stage-1 shared-backlog files unchanged, with a harness that runs their original test suite. This is the baseline every later protocol change diffs against.

The source is a sibling project at commit af5b1f8:
- scripts/shared-backlog.sh;
- scripts/hooks/pre-push;
- scripts/tests/shared-backlog-test.sh, with 75 tests.

The test expects its original folder layout, so the harness rebuilds that layout in a temp directory.

Run this task INTERACTIVELY on the host, not in Ralph: the devcontainer cannot see the source repo.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-009.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The stage-1 script, pre-push hook and test script are copied byte-identical from af5b1f8 to plugins/ralph/scripts/shared-backlog.sh, tests/shell/stage1/pre-push and tests/shell/stage1/shared-backlog-test.sh, with sha256 sums in the notes
- [ ] #2 An unchanged reference copy is kept as tests/shell/stage1/shared-backlog.sh.orig and the baseline never tests the hardened script
- [ ] #3 A pytest harness rebuilds the stage-1 layout (scripts/shared-backlog.sh, scripts/hooks/pre-push, scripts/tests/) in a temp directory and runs the unchanged test there
- [ ] #4 (host) All 75 baseline tests pass under /bin/bash 3.2
- [ ] #5 The task is run interactively on the host, not by Ralph, because the devcontainer cannot see the source repo
- [ ] #6 ruff, pytest and bats pass
<!-- AC:END -->
