---
id: TASK-46
title: 'Update README with missing flags, skills, and test docs'
status: Done
assignee:
  - '@claude'
created_date: '2026-04-20 20:12'
updated_date: '2026-04-20 20:28'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
README.md is missing: (1) --model, --prompt-file, --help, --version flags in CLI docs. (2) ralph-run, ralph-status, ralph-stop skills in Key Files table. (3) Test docs list 5 files but 13 exist — add run-summary, status-file, interrupt-trap, one-task-enforcement, run-summary-integration, status-file-integration, tee-buffering, backlog_workflow.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All current CLI flags documented including --model, --prompt-file, --help, --version
- [x] #2 Key Files table includes ralph-run, ralph-status, ralph-stop skills
- [x] #3 Test structure section lists all 13 test files
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Add missing CLI flags (--model, --prompt-file, --help, --version, --timeout) to the Error Handling Options table. (2) Add ralph-run, ralph-status, ralph-stop to Key Files table. (3) Update test files section to list all 13 .bats files across unit/integration/e2e directories.

Commit: `651c77c` - task-46: Document all CLI flags, runtime skills, and test files in README

Implemented: (1) Renamed 'Error Handling Options' table to 'CLI Options' and added --model, --timeout, --prompt-file, --devcontainer, --help, --version flags with correct defaults. (2) Added ralph-run, ralph-status, ralph-stop skills to Key Files table. (3) Reorganized test files section by directory (unit/integration/e2e) listing all 13 .bats files with descriptions.
<!-- SECTION:NOTES:END -->
