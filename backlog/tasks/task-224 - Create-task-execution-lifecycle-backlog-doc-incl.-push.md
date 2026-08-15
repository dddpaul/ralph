---
id: TASK-224
title: Create task-execution lifecycle backlog doc (incl. push)
status: Done
assignee: []
created_date: '2026-08-15 19:39'
updated_date: '2026-08-15 19:53'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a backlog document in ralph's backlog/ describing the full task execution lifecycle — from intent admission through execution to completion — including the push mechanisms that exist in this project (how ralph pushes state/updates downstream).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A backlog doc is created under backlog/docs/ via 'backlog doc create' describing the task-execution lifecycle end to end, and appears in 'backlog doc list'
- [x] #2 The doc covers intent admission: how tasks enter (brainstorm to PRD to backlog, ralph-task, and the ralph-handoff inbox), autonomous task selection (lowest-ID To Do with all deps Done), and the interactive Implementation Mode Gate
- [x] #3 The doc covers the execution phase: the Gate/Plan/Implement/Review/Done Task Lifecycle, per-task branching, fresh-context iterations, and the feedback loops (build+lint+test plus the mandatory task-reviewer)
- [x] #4 The doc covers completion and merge: bump-version.sh --auto, task-file commit, git merge --no-ff, bump-version.sh --tag, and branch delete
- [x] #5 The doc documents the push mechanisms with concrete file references: post-commit hash stamping, the post-loop git push origin master (default-on; --no-push / RALPH_NO_PUSH opt-out; three gates), version-bump governance with push.followTags and the version-bump-guard.sh pre-push guard, and the /ralph-handoff one-way cross-project push
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: create backlog/docs/doc-5 via 'backlog doc create' (type guide) titled 'Task Execution Lifecycle and Push Mechanisms'. Structure: (1) Overview + where it fits; (2) Intent admission — task creation paths (brainstorm/PRD/backlog, ralph-task, ralph-handoff inbox), autonomous selection, interactive Implementation Mode Gate, handoff acceptance gate; (3) Execution — Task Lifecycle Gate/Plan/Implement/Review/Done, per-task branch, fresh-context iteration, feedback loops, mandatory task-reviewer; (4) Completion & merge — bump-version.sh --auto, task-file commit, merge --no-ff, --tag, branch delete; (5) Push mechanisms (the downstream/state-propagation channels): post-commit hash stamping (loop.py-independent, local audit trail), post-loop 'git push origin master' (push.py: default-on, --no-push/RALPH_NO_PUSH opt-out, three gates), version-bump governance + push.followTags + version-bump-guard.sh pre-push guard, plugin-marketplace refresh via /plugin update, ralph-handoff cross-project push, status file + heartbeat for external consumers. NOTE: /ralph-sync does NOT exist as a live skill (only historical design/ references) — will not claim it. Docs-only change: no shipped plugins/ralph/** files touched, so bump-version.sh --auto will no-op (no version bump).

Done: created backlog/docs/doc-5 'Task Execution Lifecycle and Push Mechanisms' (type guide) — a navigation/reference sheet covering the 4 lifecycle stages (intent admission -> execution -> completion/merge -> push/propagation) with concrete file references. Documents every real push mechanism: post-commit hash stamping, post-loop 'git push origin master' (push.py, default-on, 3 gates), version-bump governance (bump-version.sh --auto/--tag/--nudge + push.followTags + version-bump-guard.sh pre-push guard), /plugin update marketplace refresh, /ralph-handoff cross-project push, and status file + heartbeat. Explicitly notes /ralph-sync is NOT a live mechanism (design/ references only). Gate: ruff clean, 346 pytest passed, task-reviewer APPROVED. Docs/backlog-only -> bump-version.sh --auto no-ops (no shipped plugins/ralph/** change), no version bump.
<!-- SECTION:NOTES:END -->
