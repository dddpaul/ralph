---
id: TASK-344
title: Let bump-version.sh re-bump past a resolved version conflict
status: Done
assignee: []
created_date: '2026-11-09T06:35:00Z'
updated_date: '2026-11-09T06:50:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: the 2026-11-08 feature review follow-up from TASK-342/343 (see TASK-342 notes: the macOS host hit this resolving a version conflict with origin's v0.25.12 release). .claude/RELEASING.md 'Resolving a version conflict' step 3 says to re-bump with '.claude/hooks/bump-version.sh patch' on a task branch after step 2 merges origin/master into master. But right after that merge, a fresh task branch has an empty master..HEAD diff (no shipped-set file changed vs the now-current master), so bump-version.sh's do_auto refuses:

```
bump-version: no shipped-set file changed in $BASE_REF..HEAD; nothing to bump.
```

(see .claude/hooks/bump-version.sh:169-171, shipped_changed_in_range). The host had to set both manifests by hand instead.

Separately, .claude/RELEASING.md 'The release commit rule' section (line ~24-26) defines the release commit of vX.Y.Z as the first commit along origin's master first-parent history where both manifests read X.Y.Z, but does not say what happens to a version that gets superseded by a resolved conflict. After TASK-342's re-bump, the first commit reading 0.25.12 along the new first-parent history is no longer beda54c (where origin's v0.25.12 tag points) but a different commit (7ea4fd7 on the Mac's history) — the superseded version's release-commit location moved. Nothing breaks today because version-bump-guard.sh (.claude/hooks/version-bump-guard.sh) only checks the pushed tip's current version, never a superseded one, but the doc as written implies the release-commit rule is checked for every version that ever appeared, which is misleading.

Fix:
1. Give bump-version.sh a way to re-bump both manifests above local master's version in the conflict-resolution scenario — same two-manifest edit and same commit-message format as --auto — WITHOUT requiring shipped_changed_in_range to be true first. Either add a new mode/flag for this (preferred, keeps the doc scriptable) or, if that is not a clean fit, change RELEASING.md step 3 to say to edit both manifests directly instead of invoking bump-version.sh. Pick whichever keeps the two manifests' edit and the commit-message format consistent with --auto's, and make RELEASING.md step 3 match whatever the final mechanism is.
2. Add a sentence to 'The release commit rule' section of .claude/RELEASING.md saying that a superseded version (one whose first-parent release commit location changed because a later conflict resolution replaced it) is never rechecked — version-bump-guard.sh only ever validates the pushed tip's current version.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A documented way exists to re-bump both plugin manifests above local master's version during a version-conflict resolution (RELEASING.md step 3's scenario) even when master..HEAD contains no shipped-set file change; if implemented as a bump-version.sh mode, it reuses --auto's two-manifest edit and commit-message format
- [x] #2 .claude/RELEASING.md step 3 of 'Resolving a version conflict' is updated to match the chosen mechanism exactly (no stale reference to a bump-version.sh invocation that would refuse)
- [x] #3 .claude/RELEASING.md 'The release commit rule' section states that a superseded version's release commit is never rechecked, because version-bump-guard.sh only validates the pushed tip's current version
- [x] #4 bash -n and the bash 3.2 static guard (R-INFRA-3) pass on any changed shell script
- [x] #5 ruff, pytest and bats all pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add a --rebump mode to .claude/hooks/bump-version.sh that runs do_auto's manifest edit + commit-message path without the shipped_changed_in_range precondition (default patch, combinable with patch|minor|major and --no-commit; still idempotent via already_ahead). Update RELEASING.md step 3 to use it, add the superseded-version sentence to 'The release commit rule', add bats tests.

Commit: `5994d8f` - task-344: add bump-version.sh --rebump for version-conflict re-bumps

Review: APPROVED 5994d8f0eedfb6ad2f42e1750742b6dbf5421131

Implemented bump-version.sh --rebump (do_auto with the shipped-change precondition off; patch default, combinable with patch|minor|major and --no-commit; already-ahead no-op kept). RELEASING.md step 3 now uses --rebump; release commit rule notes superseded versions are never rechecked. 4 new bats tests. ruff clean, pytest 1605 passed/4 skipped, bats 286/286.
Follow-up: bump-version.sh accepts '--auto --rebump' silently as --rebump while the error text says --rebump combines only with patch|minor|major and --no-commit; align the message or reject the pairing (reviewer minor).
<!-- SECTION:NOTES:END -->
