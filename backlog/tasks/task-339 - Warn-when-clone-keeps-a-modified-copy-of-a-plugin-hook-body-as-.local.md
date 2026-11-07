---
id: TASK-339
title: Warn when clone keeps a modified copy of a plugin hook body as .local
status: To Do
assignee: []
created_date: '2026-11-07T21:35:00Z'
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
- [ ] #1 clone warns on stderr, naming the hook and the plugin body it repeats, when an accepted hook contains the body's lines as defined in the description, and still moves it to .local with the same exit status (pytest)
- [ ] #2 An accepted hook that does not contain the body's lines gets no warning (pytest)
- [ ] #3 bash -n, the bash 3.2 static guard, ruff and pytest pass
<!-- AC:END -->
