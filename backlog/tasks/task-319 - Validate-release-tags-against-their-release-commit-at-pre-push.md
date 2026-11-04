---
id: TASK-319
title: Validate release tags against their release commit at pre-push
status: To Do
assignee: []
created_date: '2026-11-04T14:55:00Z'
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
- [ ] #1 The release commit of vX.Y.Z is defined as the first commit along origin base branch first-parent history where both manifests read X.Y.Z, and the peeled tag must point at it
- [ ] #2 `.claude/hooks/version-bump-guard.sh` looks up origin refs/tags/vX.Y.Z and its peeled ref with git ls-remote under a network deadline and compares the peeled commit
- [ ] #3 The guard refuses when origin has the tag at a different peeled commit or the two manifests disagree on the pushed tip, and refuses with a clear message when origin is unreachable
- [ ] #4 Commits after the release with the same version pass
- [ ] #5 The repo release procedure under .claude/ documents the manual re-bump after a version conflict and never moves an existing tag
- [ ] #6 Fixtures cover both sides tagging the same version, a normal bump, a post-release commit, an annotated tag, an unreachable origin and merged divergent same-version bumps
- [ ] #7 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->
