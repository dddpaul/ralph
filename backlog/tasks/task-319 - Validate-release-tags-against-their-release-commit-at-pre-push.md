---
id: TASK-319
title: Validate release tags against their release commit at pre-push
status: Done
assignee: []
created_date: '2026-11-04T14:55:00Z'
updated_date: '2026-11-04T19:30:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
This repo only: catch two hosts bumping the plugin to the same version with different content.

The release commit of vX.Y.Z is the first commit, along origin's first-parent history, where both manifests read X.Y.Z. The tag must point there.

version-bump-guard.sh compares origin's peeled tag at pre-push.

An existing tag is never moved; a version conflict is resolved by a manual re-bump.

This is repo-specific tooling under .claude/ and is not shipped in the plugin.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-025.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The release commit of vX.Y.Z is defined as the first commit along origin base branch first-parent history where both manifests read X.Y.Z (or, when that commit is a merge pulling X.Y.Z in from another parent, that parent line's release commit), and the peeled tag must point at it
- [x] #2 `.claude/hooks/version-bump-guard.sh` looks up origin refs/tags/vX.Y.Z and its peeled ref with git ls-remote under a network deadline and compares the peeled commit
- [x] #3 The guard refuses when origin has the tag at a different peeled commit or the two manifests disagree on the pushed tip, and refuses with a clear message when origin is unreachable
- [x] #4 Commits after the release with the same version pass
- [x] #5 The repo release procedure under .claude/ documents the manual re-bump after a version conflict and never moves an existing tag
- [x] #6 Fixtures cover both sides tagging the same version, a normal bump, a post-release commit, an annotated tag, an unreachable origin and merged divergent same-version bumps
- [x] #7 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: restructure version-bump-guard.sh master branch into check_bump + check_release_tag. Release-tag check: refuse if plugin.json/marketplace.json versions differ at the pushed tip; walk first-parent from the tip while both manifests read X.Y.Z to find the release commit; git ls-remote <remote> refs/tags/vX.Y.Z + ^{} under a bash-3.2-portable watchdog deadline (VERSION_GUARD_LS_REMOTE_TIMEOUT, default 20s); refuse on unreachable/timeout or a peeled commit != release commit; absent tag passes. Docs in new .claude/RELEASING.md + README pointer. Bats fixtures with a bare origin.

Commit: `32e9570` - task-319: validate release tags against their release commit at pre-push

Commit: `42d90ea` - task-319: accept a merge-pulled release as the release commit

Implemented: version-bump-guard.sh now runs check_bump then check_release_tag on master pushes. check_release_tag refuses on manifest disagreement at the tip, on an unreachable/timed-out remote (git ls-remote under a sleep-loop watchdog, VERSION_GUARD_LS_REMOTE_TIMEOUT default 20s, no GNU timeout), and when origin's peeled vX.Y.Z is not a release commit of the tip. is_release_of() accepts the first-parent release commit, or recurses into a merge's non-first parent that brought X.Y.Z in (merge pull of another host's release — found by task-reviewer as a false positive). Absent tag passes. Docs: new .claude/RELEASING.md (added to .gitignore allow-list) + README paragraph. 12 new bats fixtures (21 total). Container cannot reach GitHub, so a real-origin run blocks with the 'cannot reach' message; using the local repo as remote, the real annotated v0.18.3 passes. Checks: ruff pass, pytest 1261 passed/4 skipped, bats 0 failures. task-reviewer: APPROVED (score 9); its minor note led to AC1 text being widened to the enforced rule.
<!-- SECTION:NOTES:END -->
