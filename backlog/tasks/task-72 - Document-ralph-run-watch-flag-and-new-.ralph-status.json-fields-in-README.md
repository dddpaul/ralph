---
id: TASK-72
title: Document ralph-run watch flag and new .ralph-status.json fields in README
status: To Do
assignee: []
created_date: '2026-05-01 08:47'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-70 added the `watch=` argument to `/ralph-run` (auto-monitoring via the new `ralph-status-watch` skill) and extended `.ralph-status.json` with `iteration_started_at` plus restructured `errors[]` from a list of strings to a list of `{iteration, at, message}` objects. README.md was not updated to reflect any of these changes.

Gaps in current README:
- CLI Options table covers ralph.sh flags but not skill-level `watch` parameter
- Examples section has no `/ralph-run watch=5m` example
- Key Files / Skills section doesn't list `ralph-status-watch`
- No documentation of the new `iteration_started_at` and restructured `errors[]` shape — external consumers (dashboards, scripts) reading `.ralph-status.json` will be confused by the change

This matters because the watch feature is the primary user-facing addition since TASK-65, and users discovering the existing `/ralph-run` skill won't know it exists without reading recent task notes or skill source.

## Scope

1. **CLI Options table** — add a `watch` row documenting:
   - Default: `false`
   - Accepted values: `true` (= 5m), `false`, or a duration like `30s`, `5m`, `1h`
   - Behavior summary: \"After successful background launch, invokes /loop in dynamic mode to poll status; surfaces only interesting events (failed iteration, stuck, crashed, finished)\"

2. **Examples section** — add at least one example:
   - `/ralph-run watch=5m` — auto-monitor every 5 minutes
   - `/ralph-run tasks=70 watch=2m max_iterations=3` — combined with task whitelist

3. **Skills section / Key Files** — add `ralph-status-watch` to the list of skills with a one-line description.

4. **`.ralph-status.json` fields documentation** — add or update a section describing the JSON shape, specifically:
   - `iteration_started_at` (ISO 8601 timestamp, written at the top of each iteration)
   - `errors[]` is now a list of objects: `{iteration: <int>, at: <ISO timestamp>, message: <string>}` — NOT bare strings
   - `timeout_sec` field (already added by TASK-70)

   Note for external consumers that this is a breaking change vs older Ralph runs.

## Out of scope
- Other README rewrites or restructuring
- Updating the ralph-init skill template README (Ralph users get their own README from this repo's; templates use a different starter)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README CLI Options table includes watch row with default, accepted values, and behavior summary
- [ ] #2 README Examples section has at least one /ralph-run watch=... example
- [ ] #3 README Skills/Key Files section lists ralph-status-watch with one-line description
- [ ] #4 README documents new .ralph-status.json fields: iteration_started_at, restructured errors[] shape, timeout_sec
- [ ] #5 README notes the errors[] shape change is breaking for external consumers
<!-- AC:END -->
