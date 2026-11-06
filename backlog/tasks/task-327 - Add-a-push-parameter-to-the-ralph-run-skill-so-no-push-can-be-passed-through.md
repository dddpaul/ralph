---
id: TASK-327
title: Add a push parameter to the ralph-run skill so --no-push can be passed through
status: Done
assignee: []
created_date: '2026-11-06T15:38:00Z'
updated_date: '2026-11-06T15:53:00Z'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph.sh's push-on-complete has been enabled by default since TASK-211: push.py runs git push origin master (with push.followTags, so version tags go too) once after any run that advanced master, including after a /ralph-stop or a failed run, because the push call sits after loop.py's finally block, not inside it. --no-push is the opt-out flag.

The /ralph-run skill (plugins/ralph/skills/ralph-run/SKILL.md) has no push parameter at all and never documents that a launch pushes. Every launch through the skill therefore pushes master to origin at the end with no way to opt out and no mention that it will happen -- discovered while coordinating a multi-host Ralph setup where a 'push only after explicit go-ahead' rule turned out to never actually gate anything run through the skill.

Add a push parameter, default true (so current behavior is unchanged for anyone not using it), validated as true|false same as the other boolean skill params. When push=false, Step 4 adds --no-push to the RALPH_CMD array. Document plainly, near the other parameter docs, that a run pushes master (and its tags, via push.followTags) to origin at the end whenever master moved -- including after a stop or a failed run -- and that the git pre-push hook still runs on that push. Add push=<true|false> to the Step 5 launch-line report so the launch output states what will happen.

Out of scope: changing the default (stays push-on-by-default), making a stopped run skip the push, and any enforcing-clone / claim-before-push logic -- that belongs to TASK-312 (Publish each completed Ralph iteration through integrate in enforcing clones). Mention TASK-312 in the task notes so the two stay consistent if TASK-312 lands first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/skills/ralph-run/SKILL.md's parameter table gains a push row with default true, documented as validated true|false
- [x] #2 Step 4 of the skill adds RALPH_CMD+=(--no-push) when push=false, and leaves the array unchanged when push=true (matching current behavior)
- [x] #3 The skill plainly states, near the push parameter or the Step 4 push-flag note, that a completed run pushes master and its tags to origin whenever master moved, including after /ralph-stop or a failed run, and that the git pre-push hook still runs
- [x] #4 Step 5's launch-line report includes push=<true|false>
- [x] #5 /ralph-run push=false devcontainer=false tasks=<any To Do task> launches with --no-push in the actual command (verified by inspecting the built RALPH_CMD array or the launch log), and the task's branch work is NOT pushed to origin even though master advances
- [x] #6 /ralph-run with push omitted (or push=true) still pushes master on completion, unchanged from current behavior
- [x] #7 bash -n on ralph.sh passes and the shared infra portability rules (GNU/BSD, bash 3.2) are satisfied for any shell changes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add push row (default true, --no-push when false) + plain push-behaviour paragraph and true|false BLOCKED validation to ralph-run SKILL.md Step 1; Step 4 adds RALPH_CMD+=(--no-push) only for push=false; both Step 5 launch lines report push=<true|false>; doc-test in tests/python/test_ralph_run_push_param.py; live-verify both cases against a hermetic repo with a bare origin. Consistency note for TASK-312: TASK-312 lets --no-push in an enforcing clone only with tasks=N (claim still pushed, work not); if TASK-312 lands first or later, the skill's push=false text and validation must take on that restriction.

Commit: `3981799` - task-327: add push parameter to ralph-run that passes --no-push through

Verification (AC5/6): built RALPH_CMD per Step 4 (devcontainer=false, tasks=1) in a throwaway repo with a bare origin, with a fake claude that marks the task Done and commits to master; ran the workspace orchestrator directly (the project ralph.sh shim resolves the installed plugin, not this checkout). push=false: argv ends '--no-push', local master advanced to the fake-work commit, origin master stayed at init. push omitted: no --no-push in argv, log 'Publishing master to origin (0e44c1ce8 -> eeb92c8f6)... Published master to origin.', origin == local. AC7: no shell changes; bash -n ralph.sh OK. Gate: pytest 1346 passed, 4 skipped; new test file ruff-clean. 'ruff check .' reports 53 errors in files this task does not touch, and master reports the same set.

task-reviewer: APPROVED (score 9). Applied its minor finding: the push paragraph now names the origin-remote and RALPH_NO_PUSH conditions. Final gate: pytest 1346 passed, 4 skipped.
<!-- SECTION:NOTES:END -->
