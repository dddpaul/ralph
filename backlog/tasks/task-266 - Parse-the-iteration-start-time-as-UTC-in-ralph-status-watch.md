---
id: TASK-266
title: Parse the iteration start time as UTC in ralph-status-watch
status: In Progress
assignee: []
created_date: '2026-10-05 06:32'
updated_date: '2026-10-05 08:53'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The ralph-status-watch "stuck" rule never fires on a macOS host whose local time zone is not UTC. The skill converts the iteration start timestamp to an epoch with this line at `plugins/ralph/skills/ralph-status-watch/SKILL.md:56`:

```bash
date -d "<iteration_started_at>" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "<iteration_started_at>" +%s 2>/dev/null
```

On macOS the GNU `-d` form fails and the BSD fallback runs. BSD `date -j -f` matches the trailing Z as a literal character but still interprets the fields as LOCAL time, so the epoch is shifted by the host's UTC offset. Measured on this host (TZ=MSK, UTC+3) for 2026-10-05T06:21:39Z: without -u the result is 1791170499, with -u it is 1791181299 — exactly 10800 seconds apart. An iteration that had run for 10 minutes was computed as running for 189.

Consequence for the rule. Stuck fires when the computed elapsed time falls in the window from twice the timeout to twice the timeout plus one polling interval — with the defaults, 7200 to 7500 seconds. On a UTC+3 host the computed elapsed time is the real elapsed time plus 10800, which is already past the window at the moment the iteration starts, so the rule can never fire. West of UTC the shift is negative and the window moves hours past the point where a stuck iteration would matter. Only a host whose local zone is UTC gets the intended behaviour. The failure is silent: the watch reports nothing, which is exactly what a healthy run also looks like.

The sibling helper already does this correctly, so this is a one-flag fix with an in-repo precedent. `plugins/ralph/skills/ralph-status/scripts/utc-to-moscow.sh` line 11 uses `date -j -u -f`, and `plugins/ralph/skills/ralph-status/SKILL.md` line 67 documents it as "explicit UTC parsing". Apply the same `-u` to the watch skill's BSD branch. The GNU branch already honours the Z suffix and `+%s` is zone-independent, so adding `-u` there is harmless and keeps the two branches symmetric if preferred.

No existing test touches the watch skill. The test should extract the conversion line from SKILL.md rather than restate it, so it follows the shipped text, and run it under explicit non-UTC zones on both sides of UTC; running only on a UTC CI host would pass with the bug still present.

Optional, not required: moving the conversion into a small helper script alongside the existing ralph-status helper would make it executable code rather than prose the model reproduces. Leave that judgment to the implementer; the defect fix does not depend on it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The BSD branch of the timestamp conversion in plugins/ralph/skills/ralph-status-watch/SKILL.md parses the timestamp as UTC, matching the date -j -u -f form used by plugins/ralph/skills/ralph-status/scripts/utc-to-moscow.sh
- [x] #2 A test extracts the conversion line from the shipped SKILL.md and runs it against a fixed timestamp under TZ=Europe/Moscow and TZ=America/New_York, asserting the same correct epoch in both zones
- [ ] #3 The test fails against the current master version of the line under at least one non-UTC zone — record the observed failing epoch in the task notes
- [ ] #4 The test passes on this macOS host, where the BSD branch is the one that runs, and the result is recorded in the task notes
- [x] #5 Gates: uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C node_modules/.bin/bats tests/unit passes with no new failures relative to master
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Execution constraint: the defect is in the BSD branch, which only runs on macOS. In a Linux devcontainer the GNU date -d branch succeeds first and handles the Z suffix correctly, so a test of the full shipped line passes against the UNFIXED master version too, and AC #3 cannot be demonstrated there. Make the test target the BSD fallback explicitly where BSD date is available (and say so when it is not), and add a static assertion that the BSD branch carries -u so the container run still checks something real. AC #3 and AC #4 must be verified on the macOS host — either implement this interactively, or run it in the container and verify those two ACs on the host before marking Done.

Commit: `385e735` - task-266: parse the iteration start time as UTC in the status-watch BSD date branch

Plan: add -u to the BSD branch of the SKILL.md conversion line; pytest test extracts the line from SKILL.md, runs the full line and (where BSD date exists) the BSD branch alone under TZ=Europe/Moscow and America/New_York, plus a static assertion that the BSD branch carries -u.

Container run (Linux, GNU date 9.1, no BSD date): tests/python/test_status_watch_utc_parse.py -> 3 passed, 2 skipped (BSD-branch runtime tests skip: BSD date unavailable). Expected epoch for 2026-10-05T06:21:39Z = 1791181299. Against the master line: the static -u test FAILS; the full-line runtime tests pass in the container because GNU date -d wins first (as the task predicted). Gates: ruff clean; pytest 774 passed, 2 skipped; bats 138 tests, 1 failure (#124 R11 settings.local.json shape) identical on master -> no new failures.

PENDING host verification (cannot run in the Linux container): AC #3 - on macOS, run the BSD test against the master line (restore master's SKILL.md) under TZ=Europe/Moscow and record the failing epoch (task body predicts 1791170499); AC #4 - on macOS run uv run pytest tests/python/test_status_watch_utc_parse.py -v and confirm the 2 BSD tests PASS (not skip). Task left In Progress, branch task-266 not merged until then.

Review: task-reviewer APPROVED (0 blocking, 0 minor). Not marked Done and not merged: the task requires AC #3/#4 on the macOS host first. To finish on host: verify #3/#4, check them off, then run Task Lifecycle steps 5-6 (bump-version --auto, merge, --tag).
<!-- SECTION:NOTES:END -->
