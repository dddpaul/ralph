---
id: TASK-339
title: Warn when clone keeps a modified copy of a plugin hook body as .local
status: Done
assignee: []
created_date: '2026-11-07T21:35:00Z'
updated_date: '2026-11-08T09:23:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: migrate-plugin-hooks.sh clone moves an accepted hook that differs from the shim to <name>.local, which the shim runs before the plugin body. When that hook is a modified copy of the plugin body, the .local repeats the body's work, so it runs twice (TASK-302 F2). The fix is a report, not a refusal: the hook is accepted, so clone still moves it, and then warns that it repeats the plugin body and should be cut down to the project-only lines.

Detection: the hook contains every non-blank, non-comment line of the current plugin body of the same name (plugins/ralph/git-hooks/<name>), in order.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 clone warns on stderr, naming the hook and the plugin body it repeats, when an accepted hook contains the body's lines as defined in the description, and still moves it to .local with the same exit status (pytest)
- [x] #2 An accepted hook that does not contain the body's lines gets no warning (pytest)
- [x] #3 bash -n, the bash 3.2 static guard, ruff and pytest pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add repeats_body() (awk subsequence match of the plugin body's non-blank, non-comment lines, trimmed) to migrate-plugin-hooks.sh; in the clone shims step, for action=local warn on stderr naming the hook and plugins/ralph/git-hooks/<name>; document in header; pytest for warn and no-warn cases.

Commit: `6fd5154` - task-339: warn when clone keeps a modified copy of a plugin hook body as .local

Review: APPROVED 6fd5154344c3f7f3887120f20cb5fd27bea73513

Implemented repeats_body() in migrate-plugin-hooks.sh: an accepted hook holding every non-blank, non-comment line of plugins/ralph/git-hooks/<name> in order (trimmed, subsequence) gets a stderr warning in clone; it is still moved to .local, exit status unchanged. Docs in README and ralph-init SKILL.md. Full pytest 1566 passed; ruff check clean.

Commit: `c7060d6` - task-339: bump plugin version to 0.25.10 (patch)
<!-- SECTION:NOTES:END -->
